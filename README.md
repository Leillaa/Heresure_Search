# Agent Licence — Florida DFS License Tracker

Internal tool that tracks Florida DFS-licensed insurance agents (life /
life & health) in Broward and Miami-Dade counties: pulls the public
license registry on a schedule, stores it in Postgres, and exposes a
web viewer + an outreach-email sender for the team.

This document is a technical overview for engineers picking up or
maintaining the project. For the step-by-step ops runbook (provisioning
a server, migrating the database, updating a live deployment), see
[`deploy/README.md`](deploy/README.md).

## What it does

1. **Daily data pull** — `parser.py` downloads Florida DFS's public
   license CSV, filters it down to life/health agents in the two target
   counties, and inserts only the *new* ones into Postgres with
   `checked = false`. Existing rows (and anything staff manually set,
   like `checked` or `Personal Email`) are never touched.
2. **Web viewer** — `app.py` (Flask) shows the `licenses` table,
   paginated, with a filter for `All / Checked / Not checked` and a
   per-row "Send Email" action (currently a UI stub).
3. **Outreach** — `send_campaign.py` sends one email at a time (single
   recipient per message, rate-limited) to agents where
   `checked = false` and a business email is on file, then flips
   `checked = true` right after each successful send so re-running the
   script never double-sends.

## Architecture (production)

```
                     ┌─────────────────────────────────────────┐
                     │   DigitalOcean droplet (Ubuntu 22.04)    │
                     │                                           │
  Internet ──HTTPS──▶│  nginx :443 ──▶ gunicorn :8000 ──▶ app.py │
                     │      (Let's Encrypt via certbot)          │
                     │                          │                │
                     │                          ▼                │
                     │                   Postgres (local)        │
                     │                     licenses table         │
                     │                          ▲                │
                     │                          │                │
                     │   systemd timer (09:00 America/New_York)  │
                     │        └─▶ parser.py (download+filter+load)│
                     └─────────────────────────────────────────┘
```

- **App process**: `gunicorn` running `app.py`, managed by systemd unit
  `agent-licence.service` — restarts automatically on crash or reboot.
- **Reverse proxy**: nginx terminates TLS and forwards to gunicorn on
  `127.0.0.1:8000` (app itself is never exposed directly).
- **TLS**: a real Let's Encrypt certificate, auto-renewing. No domain was
  purchased — the site is reachable via a free `sslip.io` hostname that
  resolves to the droplet's IP (see `deploy/server.env`, not in git).
- **Scheduled data refresh**: systemd timer `agent-licence-parser.timer`
  runs `parser.py` once a day at 9:00 **America/New_York** (DST-aware).
  It's independent of anyone's laptop being on.
- **Firewall**: `ufw` — only SSH (22) and HTTP/HTTPS (80/443) are open.
- **Access**: the site currently has no login (open to anyone with the
  link) — see `BASIC_AUTH_USERS` in `.env.example` to turn on per-user
  HTTP Basic Auth later without a code change.

## Data flow

```
Florida DFS public CSV (~330MB, ~1.2M rows)
        │  parser.py: download + filter
        │  (State=FL, county in {Broward, Miami-Dade}, License Type in life/health set)
        ▼
staging_licenses.csv
        │  load_script.sql: dedupe within batch, INSERT ... WHERE NOT EXISTS
        │  (match key: Full Name + Business Email — insert-only, never overwrite)
        ▼
licenses table (Postgres)
        │
        ├──▶ app.py            (read-only web viewer, filterable by checked)
        └──▶ send_campaign.py  (reads checked=false rows, emails them, flips checked=true)
```

## Repository layout

| Path | Purpose |
|---|---|
| `app.py` | Flask web viewer (paginated table, checked/unchecked filter, Basic Auth support) |
| `parser.py` | Daily pipeline: download FL DFS registry → filter → load new agents into Postgres |
| `load_script.sql` | Insert-only-new logic used by `parser.py` (staging table → `licenses`) |
| `create_table.sql` | `licenses` table schema |
| `dedupe_licenses.sql` | One-off maintenance: collapse existing duplicate rows (same Full Name + Business Email) |
| `send_campaign.py` | Rate-limited, one-recipient-per-email outreach sender; marks `checked = true` after each send |
| `send_test_email.py` | Sends one test email to yourself to verify SMTP creds work |
| `requirements.txt` | Python dependencies |
| `.env.example` | Template for local `.env` (DB creds, SMTP creds, optional Basic Auth) — copy, fill in, never commit |
| `deploy/` | Everything needed to stand up or update the production server — see `deploy/README.md` |

Not part of the running app (kept on disk for history, gitignored,
superseded by `parser.py` which does download+filter+load in one
scheduled step): `filter_life_licenses.py`, `load_to_db.py` — an older
two-step manual version of the same pipeline.

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # fill in PGPASSWORD (and SMTP_* if testing email)

python3 app.py          # http://127.0.0.1:5000
```

Requires a local Postgres with the `licenses` table (`create_table.sql`)
and, ideally, data loaded via `parser.py` (needs `PGPASSWORD` set — see
`.env.example`).

## Configuration

All configuration is environment-based via `.env` (see `.env.example`
for the full list): Postgres connection (`PGHOST`/`PGPORT`/`PGUSER`/
`PGDATABASE`/`PGPASSWORD`), SMTP creds for outreach, and optional
`BASIC_AUTH_USERS` to require a login on the web viewer. No secret has
a hardcoded default in code — the app refuses to start without
`PGPASSWORD` set.

## Security notes

- **PII**: the `licenses` table contains real names, emails, phone
  numbers, and mailing addresses of licensed individuals. Treat exports,
  dumps, and server access accordingly.
- **Secrets** live only in `.env` (gitignored) and, in production, in
  `/opt/agent_licence/.env` on the server (mode `600`). They are never
  committed.
- **Server identity** (droplet IP, live site URL) lives in
  `deploy/server.env` (gitignored) — copy `deploy/server.env.example`
  and fill it in locally; get the real values from whoever currently
  operates the server, not from git.
- **Known history issue**: an early commit had a Postgres password
  hardcoded as a fallback default in three scripts. It has since been
  removed from the code and rotated on the server, but it still exists
  in the git history of this repository. If that password was ever
  reused anywhere else, rotate it there too.
- The web viewer currently has **no authentication** by default (open
  to anyone with the URL) — see `BASIC_AUTH_USERS` above to lock it
  down.

## Operations

See [`deploy/README.md`](deploy/README.md) for: provisioning a new
server, migrating the database, the systemd units, nginx/TLS setup, the
daily parser timer, and the one-command update flow (`deploy/update.sh`).

## License

All rights reserved — see [`LICENSE`](LICENSE). Copyright © 2026 Leila
Chernova (leila.studio). Viewing the source for personal, educational
purposes is permitted; any other use (running, deploying, copying,
modifying, redistributing) requires prior written permission from the
owner.
