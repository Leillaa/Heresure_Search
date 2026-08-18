# AGENTS.md

Working notes for AI agents on this project. Read this before making changes.

---

## 1. Instructions to follow

### 🚨 Hard rule: no file over 500 lines

**Never leave a file longer than 500 lines.** If a change produces a file over
500 lines, it MUST be refactored — split it along a real seam (a layer, a
responsibility, a feature), not at an arbitrary line number. This applies to
every file: Python, HTML, CSS, SQL, shell, config, docs.

Current state — the longest file is `scripts/parser.py` at 294 lines, so
everything is within budget. Check before you finish:

```bash
find . -path ./.git -prune -o -name '__pycache__' -prune -o -type f \
  \( -name '*.py' -o -name '*.html' -o -name '*.css' -o -name '*.js' -o -name '*.sql' -o -name '*.sh' -o -name '*.md' -o -name '*.yml' \) \
  -print0 | xargs -0 wc -l | sort -rn | head -10
```

### Other conventions

- **Bilingual comments.** Every docstring, comment block and doc section is
  written `[EN]` then `[RU]`. Match this in anything you add or edit — the
  project is read by both an English- and a Russian-speaking maintainer. Do not
  drop the RU half when editing an existing block.
- **No new dependencies without asking.** `requirements.txt` is deliberately
  four lines (Flask, psycopg2-binary, gunicorn, requests). In particular the
  `.env` parser is hand-rolled on purpose — do **not** add `python-dotenv`.
- **Run scripts as modules from the repo root**: `python3 -m scripts.parser`,
  never `python3 scripts/parser.py`. A direct path puts `scripts/` on
  `sys.path[0]` instead of the repo root, and `import app.config` dies with
  `ModuleNotFoundError`.
- **Config goes in `app/config.py` only.** Never re-add a local `load_env()` or
  a second place that reads `PGHOST`/`SMTP_*`. That duplication (4 copies) is
  what this layout removed.
- **Never commit or push unless asked.** The working tree usually carries
  uncommitted edits from the maintainer; leave them alone.

### ⚠️ Real personal data

The `licenses` table holds **real** names, emails, phone numbers and mailing
addresses of Florida insurance agents. Therefore:

- Do not paste query results, CSV rows or dumps into chat, logs, commits or
  issue text. Report counts and shapes, not records.
- `AllValidLicensesIndividual.csv`, `staging_licenses.csv`, `*.dump` and `.env`
  are gitignored **and** dockerignored. Keep them that way.
- **Never send a live email.** `scripts/send_campaign.py` and
  `scripts/send_test_email.py` contact real people. Verify with
  `--dry-run` only, and ask the maintainer before any real send.
- The web page is protected by HTTP Basic Auth (`BASIC_AUTH_USERS`). Never
  weaken or bypass it — see the decorator-order trap in §4.

---

## 2. Project structure

MVC-style Flask app plus standalone operational scripts.

```
wsgi.py                       WSGI entry point — `gunicorn wsgi:app`; also the dev server
app/
  __init__.py                 create_app() factory
  config.py                   THE config module: loads .env, exposes PG_*/auth settings
  models/
    db.py                     psycopg2 connection + connection() context manager
    license.py                every SQL statement the web app runs
  controllers/
    licenses.py               the `/` route, as a Flask blueprint
  views/
    auth.py                   require_auth — HTTP Basic Auth decorator
    filters.py                to_tel_href, registered as the `tel_href` Jinja filter
  templates/index.html        the paginated table
  static/css/main.css
  static/js/main.js           the stub "Send Email" toast
scripts/
  parser.py                   daily ETL: download FL DFS registry → filter → load
  send_campaign.py            one-at-a-time outreach; flips checked = true after each send
  send_test_email.py          SMTP smoke test (no DB)
sql/
  create_table.sql            `licenses` schema; also compose's initdb script
  load_script.sql             insert-only-new loader invoked by parser.py via psql
  dedupe_licenses.sql         one-off maintenance, run by hand
deploy/                       provision/update scripts, nginx conf, systemd units, runbook
Dockerfile docker-compose.yml .dockerignore
.env                          NOT in git. Must stay at the repo root (see §4)
```

### Layer boundaries

| Layer | Owns | Must not |
|---|---|---|
| `app/models/` | All SQL, connection lifecycle | Know about requests or HTML |
| `app/controllers/` | Query params, pagination math, choosing a template | Contain SQL |
| `app/views/` + templates | Formatting, auth decorator | Query the DB |
| `app/config.py` | Reading `.env` and the environment | Import Flask or any model |
| `scripts/` | Operational one-shots | Be imported by the web app |

### How things run

```bash
python3 wsgi.py                                       # dev server, http://127.0.0.1:5000
gunicorn -w 2 -b 127.0.0.1:8000 wsgi:app              # production (behind nginx)
python3 -m scripts.parser                             # ETL
python3 -m scripts.send_campaign --dry-run --limit 3  # safe preview
python3 -m scripts.send_test_email                    # SMTP check
docker compose up -d --build                          # full local stack + its own Postgres
```

Compose publishes Postgres on host port **5434** and the app on **8000**. The
maintainer's own `.env` points at port **5435** (a separate local Postgres) —
these are different databases, so know which one you are hitting.

---

## 3. Decisions

Recorded so they are not silently reversed.

- **`app/` package rather than root-level `models/ views/ controllers/`.**
  `Flask(__name__)` inside the package sets `root_path` to `app/`, so
  `app/templates/` and `app/static/` are auto-discovered with no
  `template_folder`/`static_folder` arguments. It is also the layout a Flask
  developer expects. Cost: the package name `app` once collided with the old
  `app.py`, which is why that file was deleted in the same change.
- **Single `app/config.py`, loaded at import.** `load_env(ENV_FILE)` runs once
  when the module is imported, *before* any constant below it is read. That
  ordering is the fix for the old `send_campaign.py` bug (§5).
- **`PGPASSWORD` is a function, not a constant.** `config.pg_password()` is
  read on demand because `send_test_email.py` needs `app.config` for SMTP
  settings but never touches Postgres, and must not be blocked by a missing DB
  password. Fail-fast is preserved by calling it once inside `create_app()`, so
  gunicorn still refuses to boot rather than erroring on the first request.
- **`PROJECT_ROOT = Path(__file__).resolve().parents[1]`.** All data and SQL
  paths are anchored to it, so the scripts behave identically under systemd,
  Docker, and a shell in any directory. `.resolve()` handles symlinked
  checkouts.
- **`to_tel_href` is a Jinja filter, not a controller step.** It formats a
  model field for display, so it belongs to the view layer. This let the
  controller stop writing a presentation key (`phone_href`) into model rows.
- **One DB connection per request, shared by both queries.** The tab counts and
  the visible page must come from the same snapshot; two connections would let
  the counts disagree with the page while `send_campaign.py` writes.
- **The `f"WHERE {where_sql}"` interpolation in `app/models/license.py` stays.**
  It is safe *only* because the value comes from the `STATUS_FILTERS`
  allowlist. `normalize_status()` lives in the same module for exactly this
  reason — keep them together, and never let a raw request value reach it.
- **No `pyproject.toml`.** `python -m` from the repo root covers both systemd
  (`WorkingDirectory=/opt/agent_licence`) and manual runs. Add one if/when a
  `tests/` directory appears and imports need resolving.
- **No `base.html`.** One page, one template. Add a base when a second page
  exists.
- **`scripts/send_campaign.py` keeps its own psql-based DB access.** Folding it
  into `app/models/license.py` would mix psql-subprocess and psycopg2 access in
  one module. Worth revisiting when the web app grows a real send endpoint.

---

## 4. Traps — things that break silently

Each of these has bitten or nearly bitten this project. None of them raise an
obvious error.

- **Decorator order on routes.** The route must be the OUTER decorator:
  ```python
  @bp.route("/")      # outer
  @require_auth       # inner
  def index(): ...
  ```
  Flip them and the blueprint registers the *unwrapped* function — **auth is
  silently bypassed**, no error, on a page serving real personal data. Always
  verify with `BASIC_AUTH_USERS` set and expect a 401.
- **`\copy` in `sql/load_script.sql`** is a *client-side* psql meta-command. Its
  path resolves against psql's own CWD, which `scripts/parser.py` pins with
  `cwd=STAGING_CSV.parent` on the subprocess. psql performs **no variable
  interpolation inside `\copy` arguments**, so `psql -v` + `:'var'` does not
  work — the filename is taken literally. Don't retry it.
- **`.env` must stay at the repo root.** `deploy/dump_db.sh` sources `./.env`,
  and both systemd units use `EnvironmentFile=/opt/agent_licence/.env`. Moving
  a Python file down a directory while keeping a `__file__`-relative `.env`
  path makes `load_env()` a silent no-op — this is why config is centralised.
- **systemd unit files are not in the rsynced tree.** They live in
  `/etc/systemd/system/`. `deploy/update.sh` only restarts the service; it does
  not reinstall units. Change an `ExecStart` and you must `cp` + `daemon-reload`
  on the server or the old command keeps running.
- **`rsync --delete` is required in `deploy/update.sh`** so files deleted
  locally also disappear from the server. It is safe because rsync never
  deletes receiver files matched by an `--exclude` (`.env`, `.venv/`, the dumps,
  the big CSVs are all protected). **Never add `--delete-excluded`** — that
  would wipe the server's `.env` and virtualenv.
- **`docker compose` initdb only runs on a fresh volume.** A wrong
  `./sql/create_table.sql` mount path makes Compose create a *directory* there
  and silently skip table creation. Test with `docker compose down -v` first.
- **`fetchall()` must happen inside the cursor/connection scope.** Returning a
  cursor, or closing the connection before the template iterates, yields an
  empty table with no error.
- **`/static/*` is unauthenticated.** Basic Auth covers the route, not Flask's
  static endpoint. Fine today (only CSS and a toast function). Never put
  anything sensitive under `app/static/`.

---

## 5. Changes

### 2026-08-18 — flat layout → MVC

Restructured the project from four root-level Python files into the layout in
§2. The largest Python file went from 493 lines to 294, and the rendered HTML
is byte-identical to before apart from `<style>`→`<link>` and inline→external
`<script>` (verified by diffing both versions against the same database).

- `app.py` (493 lines) split into `wsgi.py` + nine files under `app/`. The
  275-line inline HTML string became `app/templates/index.html` +
  `app/static/css/main.css` + `app/static/js/main.js`;
  `render_template_string` → `render_template`.
- `parser.py`, `send_campaign.py`, `send_test_email.py` → `scripts/` (git
  tracked these as renames, so history is intact).
- `create_table.sql`, `load_script.sql`, `dedupe_licenses.sql` → `sql/`.
- Four duplicate copies of `load_env()` and three of `get_required()` collapsed
  into `app/config.py`.
- **Bug fixed:** `send_campaign.py` read `PGHOST`/`PGPORT`/`PGUSER`/
  `PGDATABASE` at import, *before* its own `load_env()` ran in `main()`, so
  `.env` was silently ignored for those four and it always hit
  `localhost:5432/postgres`. It now honours `.env` — which means it may target
  a **different database than before**. Always `--dry-run` first.
- CWD-relative paths in `parser.py` anchored to `PROJECT_ROOT`; psql subprocess
  given `cwd=` so the `\copy` works from any directory.
- Entry point `app:app` → `wsgi:app`: updated in `Dockerfile`,
  `deploy/agent-licence.service`. `deploy/agent-licence-parser.service` now runs
  `-m scripts.parser`. Compose mount → `./sql/create_table.sql`.
  `deploy/update.sh` gained `--delete` plus a `__pycache__` cleanup.
- `README.md`, `deploy/README.md`, `.env.example` updated. `deploy/README.md`
  gained a one-time server-migration section (reinstall both units and
  `daemon-reload`, or gunicorn loads `app:app`, dies, and nginx returns 502).

### Outstanding / known gaps

- **No tests.** Verification is end-to-end and manual; see §2 and the
  verification section of `deploy/README.md`. Highest-value first tests: the
  401/200 auth pair (guards the trap in §4) and `to_tel_href` units.
- `sql/create_table.sql` has no index and no unique constraint on the dedupe key
  (`"Full Name"` + `"Business Email"`), so the anti-join in `load_script.sql`
  does the work.
- The "Send Email" button is still a stub — it only shows a toast. Wiring it up
  is the next feature, and is why the blueprint seam exists.
- A password (`1560`) is in git history; rotated on the server but not purged
  from history. See the end of `deploy/README.md`.
