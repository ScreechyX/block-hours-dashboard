"""FastAPI backend for PST Alert Dashboard."""

import asyncio
import os
import shutil
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

# In-memory job store: job_id → {status, progress, total, results, error}
JOBS: dict[str, dict] = {}

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Clean up temp files on shutdown
    for job in JOBS.values():
        tmp = job.get("tmp_path")
        if tmp and os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except Exception:
                pass


app = FastAPI(title="PST Alert Dashboard", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")


@app.get("/")
async def root():
    return {"message": "PST Alert Dashboard API", "docs": "/docs"}


@app.get("/api/health")
async def health():
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    return {
        "status": "ok",
        "anthropic_key_configured": bool(api_key and api_key.startswith("sk-")),
    }


@app.post("/api/upload")
async def upload_pst(
    file: UploadFile = File(...),
    api_key: Optional[str] = Form(None),
):
    if not file.filename.lower().endswith(".pst"):
        raise HTTPException(400, "Only .pst files are supported")

    effective_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
    if not effective_key:
        raise HTTPException(400, "Anthropic API key is required. Set ANTHROPIC_API_KEY env var or pass it in the form.")

    # Save uploaded file to a temp location
    suffix = Path(file.filename).suffix
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(tmp_fd)

    with open(tmp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        "status": "queued",
        "progress": 0,
        "total": 0,
        "parsed": 0,
        "results": [],
        "error": None,
        "tmp_path": tmp_path,
    }

    # Run analysis in background
    asyncio.create_task(_run_job(job_id, tmp_path, effective_key))

    return {"job_id": job_id}


async def _run_job(job_id: str, pst_path: str, api_key: str):
    from analyzer import analyze_emails
    from pst_parser import parse_pst

    job = JOBS[job_id]
    try:
        job["status"] = "parsing"
        # PST parsing is synchronous — run in thread pool
        loop = asyncio.get_event_loop()
        emails = await loop.run_in_executor(None, parse_pst, pst_path)
        job["parsed"] = len(emails)
        job["total"] = len(emails)

        job["status"] = "analyzing"

        async def progress(done: int, total: int):
            job["progress"] = done
            job["total"] = total

        results = await analyze_emails(emails, api_key, progress_callback=progress)
        job["results"] = [r.to_dict() for r in results]
        job["status"] = "done"
        job["progress"] = len(results)
        job["total"] = len(results)

    except Exception as exc:
        job["status"] = "error"
        job["error"] = str(exc)
    finally:
        try:
            os.unlink(pst_path)
        except Exception:
            pass
        job["tmp_path"] = None


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "status": job["status"],
        "progress": job["progress"],
        "total": job["total"],
        "parsed": job.get("parsed", 0),
        "error": job["error"],
        "result_count": len(job["results"]),
    }


@app.get("/api/jobs/{job_id}/results")
async def get_results(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] != "done":
        raise HTTPException(409, f"Job is not done yet (status: {job['status']})")
    return {"results": job["results"]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8765, reload=False)
