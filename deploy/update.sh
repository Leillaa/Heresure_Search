#!/usr/bin/env bash
# [EN] Run LOCALLY after you've changed the code (app/, scripts/, etc.).
# Copies the fresh code to the server and restarts the site.
# Does NOT touch .env on the server — the server passwords stay as they are.
#
# Usage:
#   ./deploy/update.sh                 # takes the server from deploy/server.env
#   ./deploy/update.sh 1.2.3.4         # or override explicitly
#
# [RU] Запускать ЛОКАЛЬНО после того, как поменяли код (app/, scripts/ и т.п.).
# Копирует свежий код на сервер и перезапускает сайт.
# .env на сервере НЕ трогает — серверные пароли остаются как есть.
#
# Использование:
#   ./deploy/update.sh                 # берёт сервер из deploy/server.env
#   ./deploy/update.sh 1.2.3.4         # или переопределить явно

set -euo pipefail
cd "$(dirname "$0")/.."

SERVER_ENV="deploy/server.env"
if [ -f "$SERVER_ENV" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$SERVER_ENV"
  set +a
fi

SERVER="${1:-${SERVER_IP:-}}"
if [ -z "$SERVER" ]; then
  echo "Server address not set." >&2
  echo "Copy deploy/server.env.example -> deploy/server.env and fill in SERVER_IP," >&2
  echo "or pass the IP as an explicit argument: ./deploy/update.sh 1.2.3.4" >&2
  exit 1
fi

REMOTE_DIR=/opt/agent_licence

echo "==> Copying code to $SERVER"
# [EN] --delete removes files on the server that no longer exist locally — without
# it the old flat-layout app.py / parser.py / *.sql linger next to the new app/,
# scripts/ and sql/ trees. Safe here because rsync never deletes receiver files
# matched by an --exclude below (.env, .venv/, the dumps and the big CSVs are all
# protected). NEVER add --delete-excluded: that would wipe the server's .env and venv.
# [RU] --delete удаляет на сервере файлы, которых больше нет локально — без него
# старые app.py / parser.py / *.sql из плоской структуры останутся рядом с новыми
# app/, scripts/ и sql/. Здесь это безопасно: rsync не удаляет на приёмнике файлы,
# попавшие в --exclude ниже (.env, .venv/, дампы и большие CSV защищены). НИКОГДА
# не добавляйте --delete-excluded: это снесёт .env и venv на сервере.
rsync -az --delete \
  --exclude='.venv/' --exclude='.venv-1/' --exclude='.git/' \
  --exclude='__pycache__/' --exclude='*.pyc' \
  --exclude='.env' --exclude='.claude/' \
  --exclude='deploy/server.env' \
  --exclude='AllValidLicensesIndividual.csv' \
  --exclude='life_licenses_broward_miamidade.txt' \
  --exclude='staging_licenses.csv' \
  --exclude='*.dump' \
  ./ "root@${SERVER}:${REMOTE_DIR}/"

echo "==> Updating dependencies (if requirements.txt changed) and restarting the service"
ssh "root@${SERVER}" "
  chown -R agentapp:agentapp ${REMOTE_DIR} &&
  find ${REMOTE_DIR} -name __pycache__ -prune -exec rm -rf {} + &&
  su - agentapp -s /bin/bash -c 'cd ${REMOTE_DIR} && .venv/bin/pip install --quiet -r requirements.txt' &&
  systemctl restart agent-licence &&
  sleep 1 &&
  systemctl is-active agent-licence
"

echo "==> Site check"
if [ -n "${SITE_URL:-}" ]; then
  curl -s -o /dev/null -w 'HTTP %{http_code}\n' "$SITE_URL"
  echo "Done: $SITE_URL"
else
  echo "Done (SITE_URL not set in deploy/server.env — skipping the HTTPS check)."
fi
