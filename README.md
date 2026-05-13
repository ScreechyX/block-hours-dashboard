# Block Hours Dashboard

A self-contained HTML dashboard for MSP block hour tracking. Import grid export reports from your ticketing system and get instant visibility into client usage, forecasting, and billing status.

Live at **[block.nightmareit.com](https://block.nightmareit.com)** (Cloudflare Access protected).

## Features

- **Import grid exports** — drag and drop `.xlsx` time entry exports to load client usage data
- **Import client list** — load your client database to auto-populate balances, SDaaS status, and client leads
- **Import block summary** — load billing summaries to auto-populate pending invoice hours and predicted balances
- **Per-client dashboard** — KPI cards, usage gauge, run-rate forecast, daily usage chart, staff breakdown, and job table
- **All-clients overview** — card grid showing every client's usage progress at a glance, sorted by criticality; SDaaS and pending invoice badges shown per card
- **Back button** — drill into a client from the all-clients view and return with a single click
- **Auto-populate** — selecting a client automatically fills in the current balance and pending invoice from imported data; balance defaults to 0 when no data is available
- **Current month auto-snap** — selecting a client or importing a file automatically snaps the period filter to the current month
- **Monthly usage trend chart** — when viewing the current month for a single client, shows a bar chart of charged hours across all previously imported months, with a dashed average line and a linear-regression trend line
- **Usage alerts** — colour-coded warnings at 50%, 75%, and 90% of block hours used
- **Ticket flags** — highlights tickets over 10 charged hours (red) and tickets where worked hours don't match charged hours (yellow / unbilled)
- **Run-rate forecasting** — projects end-of-month usage based on daily burn rate
- **Import history** — the last 8 imported files are saved in the sidebar; click any entry to reload that import's data without re-importing the file
- **Persistent settings** — block hours balance, pending invoice, monthly history, and import data are saved between sessions

## Usage

1. Open `index.html` in any modern browser — no server or installation required
2. **Optional:** Import a client list and/or block summary to enable auto-population and the all-clients overview
3. Import a grid export `.xlsx` from your ticketing system
4. Select a client from the filter to view their detailed dashboard, or leave on **All Clients** for the overview

## File Inputs

| File | Purpose |
|------|---------|
| Grid export | Time entries — staff, dates, tickets, hours worked and charged |
| Client list | Client database — codes, SDaaS status, client leads, block hour balances |
| Block summary | Billing summary — pending invoice hours, current and predicted balances |

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
