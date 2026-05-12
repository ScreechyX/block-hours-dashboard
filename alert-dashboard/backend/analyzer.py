"""Analyze parsed emails with Claude to categorize alerts and extract key info."""

import asyncio
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional

import anthropic

from pst_parser import ParsedEmail

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4, "unknown": 5}

CATEGORIES = [
    "System Error",
    "Security Alert",
    "Performance",
    "Network",
    "Database",
    "Application",
    "Infrastructure",
    "Backup/Recovery",
    "Compliance",
    "Other",
]

ANALYSIS_PROMPT = """You are an IT alert triage system. Analyze this alert email and respond with ONLY a JSON object — no markdown, no explanation.

Email details:
Subject: {subject}
From: {sender}
Date: {date}
Body:
{body}

Respond with this exact JSON structure:
{{
  "severity": "<critical|high|medium|low|info>",
  "category": "<one of: System Error, Security Alert, Performance, Network, Database, Application, Infrastructure, Backup/Recovery, Compliance, Other>",
  "affected_system": "<name of affected system/service or 'Unknown'>",
  "summary": "<1-2 sentence plain-English summary of the alert>",
  "recommended_action": "<specific recommended action, or 'Monitor' if no action needed>",
  "needs_immediate_attention": <true|false>,
  "tags": ["<relevant tag>", ...]
}}

Severity guide:
- critical: service down, data loss, security breach, production outage
- high: degraded service, failed backups, high error rates, security warnings
- medium: warnings that need attention soon, approaching thresholds
- low: informational warnings, minor issues
- info: routine notifications, success confirmations"""


@dataclass
class AnalyzedEmail:
    id: str
    subject: str
    sender: str
    date: Optional[str]
    folder: str
    body_preview: str
    severity: str
    category: str
    affected_system: str
    summary: str
    recommended_action: str
    needs_immediate_attention: bool
    tags: list[str]
    analysis_error: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


def _format_date(date) -> Optional[str]:
    if date is None:
        return None
    if isinstance(date, datetime):
        return date.isoformat()
    try:
        return str(date)
    except Exception:
        return None


def _is_alert_email(email: ParsedEmail) -> bool:
    """Filter to likely-alert emails — skip receipts, newsletters, etc."""
    subject_lower = (email.subject or "").lower()
    body_lower = (email.body or "").lower()[:500]

    alert_keywords = [
        "alert", "alarm", "error", "warning", "critical", "failure", "failed",
        "down", "offline", "outage", "incident", "issue", "problem", "fault",
        "exception", "threshold", "breach", "unauthorized", "intrusion",
        "backup", "monitor", "nagios", "zabbix", "pagerduty", "opsgenie",
        "cloudwatch", "datadog", "grafana", "prometheus", "solarwinds",
        "servicenow", "jira", "high cpu", "memory", "disk", "latency",
    ]
    return any(kw in subject_lower or kw in body_lower for kw in alert_keywords)


async def _analyze_single(client: anthropic.AsyncAnthropic, email: ParsedEmail) -> AnalyzedEmail:
    date_str = _format_date(email.date) or "Unknown"
    body_preview = (email.body or "")[:300] + "..." if len(email.body or "") > 300 else (email.body or "")

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system="You are an IT alert triage system. Always respond with valid JSON only.",
            messages=[{
                "role": "user",
                "content": ANALYSIS_PROMPT.format(
                    subject=email.subject or "(no subject)",
                    sender=email.sender or "Unknown",
                    date=date_str,
                    body=(email.body or "")[:3000],
                ),
            }],
        )

        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'\s*```$', '', raw, flags=re.MULTILINE)
        data = json.loads(raw)

        return AnalyzedEmail(
            id=email.id,
            subject=email.subject or "(no subject)",
            sender=email.sender or "Unknown",
            date=date_str if date_str != "Unknown" else None,
            folder=email.folder,
            body_preview=body_preview,
            severity=data.get("severity", "unknown").lower(),
            category=data.get("category", "Other"),
            affected_system=data.get("affected_system", "Unknown"),
            summary=data.get("summary", ""),
            recommended_action=data.get("recommended_action", "Review"),
            needs_immediate_attention=bool(data.get("needs_immediate_attention", False)),
            tags=data.get("tags", []),
        )
    except Exception as exc:
        return AnalyzedEmail(
            id=email.id,
            subject=email.subject or "(no subject)",
            sender=email.sender or "Unknown",
            date=date_str if date_str != "Unknown" else None,
            folder=email.folder,
            body_preview=body_preview,
            severity="unknown",
            category="Other",
            affected_system="Unknown",
            summary="Analysis failed",
            recommended_action="Manual review required",
            needs_immediate_attention=False,
            tags=[],
            analysis_error=str(exc),
        )


async def analyze_emails(
    emails: list[ParsedEmail],
    api_key: str,
    progress_callback=None,
    concurrency: int = 5,
) -> list[AnalyzedEmail]:
    """Analyze a list of emails concurrently, returning sorted results."""
    client = anthropic.AsyncAnthropic(api_key=api_key)

    # Filter to alert-like emails first
    alert_emails = [e for e in emails if _is_alert_email(e)]
    # If nothing matched the filter, analyze all (user explicitly imported them)
    if not alert_emails:
        alert_emails = emails

    semaphore = asyncio.Semaphore(concurrency)
    results: list[AnalyzedEmail] = []
    total = len(alert_emails)

    async def bounded(email: ParsedEmail, index: int):
        async with semaphore:
            result = await _analyze_single(client, email)
            results.append(result)
            if progress_callback:
                await progress_callback(index + 1, total)

    await asyncio.gather(*[bounded(e, i) for i, e in enumerate(alert_emails)])

    results.sort(key=lambda x: (SEVERITY_ORDER.get(x.severity, 5), not x.needs_immediate_attention))
    return results
