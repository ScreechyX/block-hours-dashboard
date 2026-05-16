import sys, json, os
import subprocess

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

# Separate profile so we don't conflict with the running Edge instance
EDGE_PROFILE = os.path.join(
    os.environ.get('LOCALAPPDATA', ''),
    'Microsoft', 'Edge', 'AdonisProfile'
)

def parse(html):
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
    required = ['Code', 'Name', 'Client Team', 'Block Hour', 'Block Hours', 'SdaaS']
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
        try:
            balance = float(texts[idx['Block Hours']])
        except (ValueError, IndexError):
            balance = 0.0
        sdaas = texts[idx['SdaaS']].strip()
        clients.append({
            'code': code,
            'name': name,
            'currentBalance': balance,
            'status': 'OK' if balance >= 0 else 'ACTION REQUIRED',
            'sdaas': sdaas
        })
    return clients, None


def main():
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

                # If redirected to SSO, wait for the user to log in then navigate to client list
                if 'microsoftonline.com' in page.url or 'my-stats' in page.url or 'login' in page.url:
                    try:
                        # Wait until we're back on any Adonis page (login complete)
                        page.wait_for_url(f'{BASE}/**', timeout=180000)
                    except Exception:
                        print(json.dumps({'error': 'Login timed out — please log in to the Edge window that opened and try again.'}))
                        return
                    # Now navigate to the client list
                    page.goto(CLIENT_URL, timeout=90000, wait_until='domcontentloaded')

                # Wait for the client table to fully render
                page.wait_for_selector('table tr td', timeout=90000)
                content = page.content()
            finally:
                ctx.close()

    except Exception as e:
        msg = str(e)
        if 'user data directory is already in use' in msg.lower():
            print(json.dumps({'error': 'Edge is already open with this profile. Close Edge and try again, or leave Edge open and try — it may work automatically.'}))
        else:
            print(json.dumps({'error': f'Browser error: {msg}'}))
        return

    clients, err = parse(content)
    if err:
        print(json.dumps({'error': err}))
        return

    print(json.dumps({'clients': clients, 'count': len(clients)}))


main()
