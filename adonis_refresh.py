import sys, json
import subprocess

def ensure(pkg, import_as=None):
    try:
        __import__(import_as or pkg)
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

ensure('browser_cookie3')
ensure('requests')
ensure('beautifulsoup4', 'bs4')

import requests
import browser_cookie3
from bs4 import BeautifulSoup

URL = 'https://adonis.atlanticdigital.com.au/adonis/client/index'

def get_session():
    for loader in (browser_cookie3.edge, browser_cookie3.chrome):
        try:
            s = requests.Session()
            s.cookies.update(loader(domain_name='atlanticdigital.com.au'))
            return s
        except Exception:
            continue
    return None

def parse(html):
    soup = BeautifulSoup(html, 'html.parser')
    # Find the header row containing Code / Name / Client Team
    headers = None
    all_rows = soup.find_all('tr')
    for row in all_rows:
        cells = row.find_all(['th', 'td'])
        texts = [c.get_text(strip=True) for c in cells]
        if 'Code' in texts and 'Name' in texts and 'Client Team' in texts:
            headers = texts
            break
    if not headers:
        return None, 'Could not find table header row'

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
    session = get_session()
    if not session:
        print(json.dumps({'error': 'Could not load browser session. Make sure Edge or Chrome is open and you are logged into Adonis.'}))
        return

    try:
        resp = session.get(URL, timeout=15)
    except Exception as e:
        print(json.dumps({'error': f'Request failed: {e}'}))
        return

    if resp.status_code != 200:
        print(json.dumps({'error': f'Adonis returned HTTP {resp.status_code}. You may need to log in first.'}))
        return

    clients, err = parse(resp.text)
    if err:
        print(json.dumps({'error': err}))
        return

    print(json.dumps({'clients': clients, 'count': len(clients)}))

main()
