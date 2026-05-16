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

BASE        = 'https://adonis.atlanticdigital.com.au'
START_URL   = f'{BASE}/adonis/site/my-stats'
CLIENT_URL  = f'{BASE}/adonis/client/index'

def get_session():
    for loader in (browser_cookie3.edge, browser_cookie3.chrome):
        try:
            s = requests.Session()
            cookies = loader(domain_name='atlanticdigital.com.au')
            s.cookies.update(cookies)
            names = [c.name for c in cookies]
            return s, names
        except Exception:
            continue
    return None, []

def is_logged_out(url):
    """Return True if the URL looks like a logged-out redirect."""
    return 'my-stats' in url or 'login' in url or 'site/index' in url

def find_team_filter(soup):
    """
    Look for a search form with a client-team select/input and return
    (field_name, option_value) for 'Commercial Team - Elliot', or None.
    """
    for select in soup.find_all('select'):
        for opt in select.find_all('option'):
            if 'elliot' in opt.get_text(strip=True).lower():
                return select.get('name'), opt.get('value', opt.get_text(strip=True))
    # Also check text inputs whose name hints at team
    for inp in soup.find_all('input'):
        name = inp.get('name', '')
        if 'team' in name.lower() or 'client_team' in name.lower():
            return name, 'Commercial Team - Elliot'
    return None, None

def fetch_client_page(session):
    """
    Navigate to the client list and apply the Commercial Team - Elliot filter.
    Returns (response, error).
    """
    # First load the unfiltered page to find the filter form
    try:
        r = session.get(CLIENT_URL, timeout=60)
    except Exception as e:
        return None, f'Request failed loading client list: {e}'

    if r.status_code != 200:
        return None, f'Adonis returned HTTP {r.status_code} on client list'

    if is_logged_out(r.url):
        return None, f'Session expired — please log in to Adonis in your browser and try again. (redirected to: {r.url})'

    soup = BeautifulSoup(r.text, 'html.parser')

    field_name, field_value = find_team_filter(soup)
    if field_name and field_value:
        # Resubmit with the filter applied
        try:
            r = session.get(CLIENT_URL, params={field_name: field_value}, timeout=60)
        except Exception as e:
            return None, f'Request failed applying filter: {e}'

    return r, None

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
        hint = f' (rows found: {found})' if found else ' (no table rows — page may require login)'
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
    session, cookie_names = get_session()
    if not session:
        print(json.dumps({'error': 'Could not load browser session. Make sure Edge or Chrome is open and logged into Adonis.'}))
        return

    resp, err = fetch_client_page(session)
    if err:
        print(json.dumps({'error': err + f' | cookies loaded: {cookie_names}'}))
        return

    clients, err = parse(resp.text)
    if err:
        print(json.dumps({'error': err}))
        return

    print(json.dumps({'clients': clients, 'count': len(clients)}))

main()
