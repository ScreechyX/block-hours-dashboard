# Block Hours Dashboard

A self-contained HTML dashboard for MSP block hour tracking. Pull live data from Adonis with one click and get instant visibility into client usage, forecasting, and billing status.

Live at **[block.nightmareit.com](https://block.nightmareit.com)** (Cloudflare Access protected).

## Features

- **Job Import** — scrapes Adonis jobs filtered to the current month and block charge type, exports to Excel 2007+, and imports directly into the dashboard; auto-starts the local Adonis server via URI scheme
- **Block Summary Refresh** — scrapes each client's block-overview page in Adonis and populates balances, pending jobs, pending invoice, and predicted balance
- **Per-client dashboard** — KPI cards, usage gauge, run-rate forecast, daily usage chart, staff breakdown, and job table
- **All-clients overview** — card grid showing every client's usage progress at a glance, sorted by criticality; Block, SDaaS, SDaaS Secure+, and Pending badges shown per card
- **Back button** — drill into a client from the all-clients view and return with a single click
- **Auto-populate** — selecting a client automatically fills in the current balance and pending invoice from imported data; balance defaults to 0 when no data is available
- **Current month auto-snap** — selecting a client or importing a file automatically snaps the period filter to the current month
- **Monthly usage trend chart** — bar chart of charged hours across all previously imported months, with a dashed average line and a linear-regression trend line
- **Usage alerts** — colour-coded warnings at 50%, 75%, and 90% of block hours used
- **Ticket links** — ticket numbers link directly to the Halo helpdesk ticket
- **Ticket flags** — highlights tickets over 10 charged hours (red) and tickets where worked hours don't match charged hours (yellow / unbilled)
- **Senior flag** — jobs containing `* Senior/Specialist Support` in their description are flagged with an amber **Senior** badge
- **Run-rate forecasting** — projects end-of-month usage based on daily burn rate
- **Import history** — the last 8 imported files are saved in the sidebar; click any entry to reload that import's data without re-importing the file
- **Persistent settings** — block hours balance, pending invoice, monthly history, and import data are saved between sessions

## Setup (Adonis integration)

The Job Import and Block Summary Refresh buttons communicate with a local Python server (`adonis_refresh.py`) that drives a browser session to scrape Adonis.

1. Install Python and run `pip install playwright beautifulsoup4` then `playwright install msedge`
2. Run `setup-adonis.ps1` once to register the `adonis-refresh://` URI scheme — this allows the dashboard to auto-start the server
3. Click **Block Summary Refresh** or **Job Import** — Edge will open, log in to Adonis via SSO if prompted, then close automatically once data is collected

## Usage

1. Open the dashboard in any modern browser (or visit the live URL)
2. Click **Block Summary Refresh** to pull client balances from Adonis
3. Click **Job Import** to pull this month's block hour jobs from Adonis
4. Select a client from the filter to view their detailed dashboard, or leave on **All Clients** for the overview

## Threshold Colours

| Colour | Meaning |
|--------|---------|
| Green | Under 75% of block hours used |
| Amber | 75–89% used — caution |
| Red | 90%+ used — action required |

## Ticket Flags

| Flag | Meaning |
|------|---------|
| ⚠ High (red) | Ticket has accumulated more than 10 charged hours |
| ⚠ Unbilled (yellow) | Worked hours do not match charged hours |

---

# Alert Dashboard

A self-contained HTML dashboard for monitoring and triaging MSP alert emails. Point it at a folder of `.eml` files and it automatically analyses severity, categorises alerts, identifies the affected client, and builds a priority queue — no server, API key, or external service required.

Located at `alert-dashboard/dashboard.html`.

## Features

- **Auto-classification** — rule-based engine categorises every alert into Network, Performance, Storage, Security, Email Security, Backup/Recovery, Infrastructure, System, Telephony, Power, or Info
- **Severity triage** — assigns Critical / High / Medium / Low / Info based on subject content, escalation flags, and resolution status
- **Client identification** — maps hostnames, domain names, and subject patterns to client codes from the CRM directory; unknown codes are flagged with a `?` chip
- **Priority queue** — sidebar showing the most urgent unresolved alerts at a glance
- **Summary cards** — total alerts, critical count, high count, and unresolved count updated in real time
- **Charts** — doughnut charts breaking down alerts by severity and by category
- **Live folder monitoring** — auto-refreshes every 60 seconds; filter selections are preserved across refreshes
- **Filters** — search, severity, category, client, system, auto-resolved status, and date range
- **Mark as resolved** — resolve individual alerts or bulk-resolve a selection; resolved alerts move to a `Resolved/` subfolder
- **Detail panel** — click any alert to see full analysis: summary, recommended action, tags, affected system, client chip, and email body preview
- **Persistent resolved state** — resolved alert IDs are stored in `localStorage` and restored on next load

## Usage

1. Open `alert-dashboard/dashboard.html` in a Chromium-based browser (Chrome, Edge — required for the File System Access API)
2. Click **Open Folder** and select the folder containing your `.eml` alert files
3. Grant read/write permission when prompted (required for moving resolved alerts)
4. The dashboard scans the folder, analyses every alert, and displays the priority queue and table
5. The folder is re-scanned automatically every 60 seconds

## Alert Categories

| Category | Covers |
|----------|--------|
| Network | Interface down, ping/DNS/RDP failures, VPN outages, PRTG notifications |
| Performance | CPU, memory, swap usage alerts |
| Storage | Disk space, disk I/O, NAS snapshots |
| Security | Firewall, blacklist, SentinelOne, password hash sync, SMTP relay |
| Email Security | DMARC aggregate reports, SPF/DKIM failures |
| Backup/Recovery | CrashPlan, backup job alerts |
| Infrastructure | Zabbix proxy, service restarts, uptime alerts |
| System | Logwatch, RAID, iDRAC/DRA hardware events, drive health |
| Telephony | 3CX alerts |
| Power | UPS events |
| Info | Marketing emails, renewal notices, informational notifications |

## Severity Levels

| Severity | Meaning |
|----------|---------|
| Critical | Escalation repeats or confirmed outages requiring immediate attention |
| High | Active problems — service down, ping failure, high resource usage |
| Medium | Warnings, resolved alerts, or events needing review |
| Low | Informational system events (logwatch, iDRAC, drive health) |
| Info | Noise — marketing, renewals, auto-notifications |
