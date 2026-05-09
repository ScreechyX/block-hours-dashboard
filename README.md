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
- **Persistent settings** — block hours balance, pending invoice, and monthly history are saved between sessions

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
