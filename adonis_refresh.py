import sys, json, os, re, base64, tempfile
import subprocess
import calendar
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 3001

def ensure(pkg, import_as=None):
    try:
        __import__(import_as or pkg)
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

ensure('playwright')
ensure('beautifulsoup4', 'bs4')

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

BASE       = 'https://adonis.atlanticdigital.com.au'
CLIENT_URL = f'{BASE}/adonis/client/index'

EDGE_PROFILE = os.path.join(
    os.environ.get('LOCALAPPDATA', ''),
    'Microsoft', 'Edge', 'AdonisProfile'
)

SUMMARY_FIELDS = {
    'Current Block Hour Balance': 'currentBalance',
    'Pending Block Hour Jobs':    'pendingJobs',
    'Pending Block Hour Invoice': 'pendingInvoice',
    'Default Re-Invoice Block Hours': 'defaultReInvoice',
    'Re-Invoice Threshold':       'reInvoiceThreshold',
    'Predicted Balance':          'predictedBalance',
}

def parse_client_list(html):
    soup = BeautifulSoup(html, 'html.parser')
    headers = None
    all_rows = soup.find_all('tr')
    for row in all_rows:
        cells = row.find_all(['th', 'td'])
        texts = [c.get_text(strip=True) for c in cells]
        if 'Code' in texts and 'Name' in texts and 'Client Team' in texts:
            headers = texts
            break
    if not headers:
        found = []
        for row in all_rows[:5]:
            cells = row.find_all(['th', 'td'])
            texts = [c.get_text(strip=True) for c in cells if c.get_text(strip=True)]
            if texts:
                found.append(texts)
        hint = f' (rows found: {found})' if found else ' (no table rows found)'
        return None, 'Could not find table header row' + hint

    idx = {h: i for i, h in enumerate(headers)}
    required = ['Code', 'Name', 'Client Team', 'Block Hour', 'SdaaS']
    missing = [r for r in required if r not in idx]
    if missing:
        return None, f'Missing columns: {missing}'

    clients = []
    header_found = False
    for row in all_rows:
        cells = row.find_all(['th', 'td'])
        texts = [c.get_text(strip=True) for c in cells]
        if not header_found:
            if texts == headers:
                header_found = True
            continue
        if len(texts) < len(headers):
            continue
        if texts[idx['Client Team']] != 'Commercial Team - Elliot':
            continue
        if texts[idx['Block Hour']] != 'Yes':
            continue
        code = texts[idx['Code']].strip()
        name = texts[idx['Name']].strip()
        if not code or not name:
            continue

        client_id = None
        for a in row.find_all('a', href=True):
            m = re.search(r'client_id=(\d+)', a['href'])
            if m:
                client_id = m.group(1)
                break
        if not client_id:
            continue

        clients.append({
            'code':     code,
            'name':     name,
            'clientId': client_id,
            'sdaas':    texts[idx['SdaaS']].strip(),
        })
    return clients, None


def parse_block_overview(html):
    soup = BeautifulSoup(html, 'html.parser')
    result = {}
    for row in soup.find_all('tr'):
        cells = row.find_all(['th', 'td'])
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True)
            if label in SUMMARY_FIELDS:
                try:
                    val = cells[1].get_text(strip=True).replace(',', '')
                    result[SUMMARY_FIELDS[label]] = float(val)
                except (ValueError, IndexError):
                    result[SUMMARY_FIELDS[label]] = 0.0
    return result


def scrape():
    clients = []
    try:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=EDGE_PROFILE,
                channel='msedge',
                headless=False,
                args=['--no-first-run', '--no-default-browser-check']
            )
            try:
                page = ctx.new_page()
                page.goto(CLIENT_URL, timeout=90000, wait_until='domcontentloaded')

                if 'microsoftonline.com' in page.url or 'my-stats' in page.url or 'login' in page.url:
                    try:
                        page.wait_for_url(f'{BASE}/**', timeout=180000)
                    except Exception:
                        return {'error': 'Login timed out — please log in to the Edge window that opened and try again.'}
                    page.goto(CLIENT_URL, timeout=90000, wait_until='domcontentloaded')

                page.wait_for_selector('table tr td', timeout=90000)
                clients, err = parse_client_list(page.content())
                if err:
                    return {'error': err}

                for client in clients:
                    url = f'{BASE}/adonis/client/block-overview?client_id={client["clientId"]}'
                    page.goto(url, timeout=60000, wait_until='domcontentloaded')
                    try:
                        page.wait_for_selector('table', timeout=30000)
                    except Exception:
                        pass
                    overview = parse_block_overview(page.content())
                    client.update(overview)
                    balance = client.get('currentBalance', 0)
                    client['status'] = 'OK' if balance >= 0 else 'ACTION REQUIRED'

            finally:
                ctx.close()

    except Exception as e:
        msg = str(e)
        if 'user data directory is already in use' in msg.lower():
            return {'error': 'AdonisProfile is already in use. Close any other Adonis refresh windows and try again.'}
        return {'error': f'Browser error: {msg}'}

    return {'clients': clients, 'count': len(clients)}


def jobs_url_for_current_month():
    today = date.today()
    first = today.replace(day=1).strftime('%d/%m/%Y')
    last  = today.replace(day=calendar.monthrange(today.year, today.month)[1]).strftime('%d/%m/%Y')
    from urllib.parse import urlencode
    params = [
        ('JobSearch[job_date]', f'{first} - {last}'),
        ('JobSearch[charge_type_list][]', 'block'),
    ]
    return f'{BASE}/adonis/job/index?' + urlencode(params)

def scrape_jobs():
    jobs_url = jobs_url_for_current_month()
    try:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=EDGE_PROFILE,
                channel='msedge',
                headless=False,
                args=['--no-first-run', '--no-default-browser-check']
            )
            try:
                page = ctx.new_page()
                page.goto(jobs_url, timeout=90000, wait_until='domcontentloaded')

                if 'microsoftonline.com' in page.url or 'my-stats' in page.url or 'login' in page.url:
                    try:
                        page.wait_for_url(f'{BASE}/**', timeout=180000)
                    except Exception:
                        return {'error': 'Login timed out — please log in to the Edge window that opened and try again.'}
                    page.goto(jobs_url, timeout=90000, wait_until='domcontentloaded')

                page.wait_for_selector('table tr td', timeout=90000)

                # Open Export Formats dropdown — try common button text variants
                export_btn = None
                for sel in [
                    'button:has-text("Export Formats")',
                    'button:has-text("Export Data")',
                    'button:has-text("Export")',
                    'a:has-text("Export Formats")',
                    'a:has-text("Export")',
                ]:
                    try:
                        page.wait_for_selector(sel, timeout=5000)
                        export_btn = sel
                        break
                    except Exception:
                        continue
                if not export_btn:
                    raise Exception('Could not find Export button on jobs page')
                page.click(export_btn)

                # Wait for any xlsx export link (id ends with -xlsx)
                page.wait_for_selector('[id$="-xlsx"]', state='visible', timeout=10000)

                with page.expect_download(timeout=120000) as dl:
                    page.click('[id$="-xlsx"]')
                download = dl.value

                tmp_path = os.path.join(tempfile.gettempdir(), download.suggested_filename)
                download.save_as(tmp_path)
                filename = download.suggested_filename

            finally:
                ctx.close()

    except Exception as e:
        msg = str(e)
        if 'user data directory is already in use' in msg.lower():
            return {'error': 'AdonisProfile is already in use. Close any other Adonis refresh windows and try again.'}
        return {'error': f'Browser error: {msg}'}

    with open(tmp_path, 'rb') as f:
        encoded = base64.b64encode(f.read()).decode('utf-8')
    os.unlink(tmp_path)
    return {'filename': filename, 'data': encoded}


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == '/ping':
            body = b'{"ok":true}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._cors()
            self.end_headers()
            self.wfile.write(body)
        elif self.path == '/job-import':
            result = scrape_jobs()
            body = json.dumps(result).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._cors()
            self.end_headers()
            self.wfile.write(body)
        elif self.path == '/refresh':
            result = scrape()
            body = json.dumps(result).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._cors()
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    try:
        server = HTTPServer(('localhost', PORT), Handler)
    except OSError:
        sys.exit(0)
    print(f'Adonis refresh server running on http://localhost:{PORT}/refresh')
    print('Leave this window open. You can now use the dashboard from anywhere.')
    server.serve_forever()
