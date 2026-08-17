#!/usr/bin/env bash
# Запускать ЛОКАЛЬНО после того, как поменяли код (app.py и т.п.).
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
  echo "Не задан адрес сервера." >&2
  echo "Скопируй deploy/server.env.example -> deploy/server.env и впиши SERVER_IP," >&2
  echo "либо передай IP явным аргументом: ./deploy/update.sh 1.2.3.4" >&2
  exit 1
fi

REMOTE_DIR=/opt/agent_licence

echo "==> Копирую код на $SERVER"
rsync -az \
  --exclude='.venv/' --exclude='.venv-1/' --exclude='.git/' \
  --exclude='__pycache__/' --exclude='*.pyc' \
  --exclude='.env' --exclude='.claude/' \
  --exclude='deploy/server.env' \
  --exclude='AllValidLicensesIndividual.csv' \
  --exclude='life_licenses_broward_miamidade.txt' \
  --exclude='staging_licenses.csv' \
  --exclude='*.dump' \
  ./ "root@${SERVER}:${REMOTE_DIR}/"

echo "==> Обновляю зависимости (если менялся requirements.txt) и перезапускаю сервис"
ssh "root@${SERVER}" "
  chown -R agentapp:agentapp ${REMOTE_DIR} &&
  su - agentapp -s /bin/bash -c 'cd ${REMOTE_DIR} && .venv/bin/pip install --quiet -r requirements.txt' &&
  systemctl restart agent-licence &&
  sleep 1 &&
  systemctl is-active agent-licence
"

echo "==> Проверка сайта"
if [ -n "${SITE_URL:-}" ]; then
  curl -s -o /dev/null -w 'HTTP %{http_code}\n' "$SITE_URL"
  echo "Готово: $SITE_URL"
else
  echo "Готово (SITE_URL не задан в deploy/server.env — пропускаю проверку по HTTPS)."
fi
