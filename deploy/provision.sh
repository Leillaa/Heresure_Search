#!/usr/bin/env bash
# Одноразовый bootstrap ЧИСТОГО droplet'а (Ubuntu 22.04) под это приложение.
# Запускать НА СЕРВЕРЕ от root сразу после создания droplet'а:
#
#   bash provision.sh '<пароль_для_БД_agents_app>'
#
# Пароль для роли agents_app в Postgres придумай сам (например: openssl rand -base64 24)
# и не теряй — он же пойдёт в .env как PGPASSWORD.

set -euo pipefail

DB_PASSWORD="${1:?Использование: bash provision.sh <пароль_для_роли_agents_app>}"

APP_USER="agentapp"
APP_DIR="/opt/agent_licence"
DB_NAME="Agents_Heresure"
DB_USER="agents_app"

echo "==> apt update и установка пакетов"
apt-get update -y
apt-get install -y python3-venv python3-pip postgresql postgresql-contrib nginx ufw git

echo "==> firewall (открываем только SSH и HTTP/HTTPS)"
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo "==> системный пользователь под приложение (без shell, без sudo)"
id -u "$APP_USER" &>/dev/null || useradd --system --create-home --shell /usr/sbin/nologin "$APP_USER"

echo "==> каталог приложения"
mkdir -p "$APP_DIR"
chown "$APP_USER":"$APP_USER" "$APP_DIR"

echo "==> роль и база в Postgres"
sudo -u postgres psql -v ON_ERROR_STOP=1 -c "
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_USER}') THEN
    CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD}';
  ELSE
    ALTER ROLE ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
  END IF;
END
\$\$;
"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}'" | grep -q 1 || \
  sudo -u postgres createdb -O "$DB_USER" "$DB_NAME"

echo
echo "======================================================================"
echo "Готово. Дальше вручную (см. deploy/README.md):"
echo "  1) залить код в $APP_DIR (git clone https://github.com/Leillaa/Heresure_Search.git)"
echo "  2) su - $APP_USER -s /bin/bash -c \"cd $APP_DIR && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt\""
echo "  3) создать $APP_DIR/.env (по образцу .env.example):"
echo "       PGHOST=localhost"
echo "       PGUSER=${DB_USER}"
echo "       PGDATABASE=${DB_NAME}"
echo "       PGPASSWORD=${DB_PASSWORD}"
echo "     (BASIC_AUTH_USERS не заполняйте — сайт пока открыт без логина/пароля)"
echo "  4) залить дамп базы (scp) и восстановить:"
echo "       PGPASSWORD=${DB_PASSWORD} deploy/restore_db.sh /root/agents_heresure_*.dump"
echo "  5) поставить systemd unit (deploy/agent-licence.service) и nginx (deploy/nginx.conf)"
echo "======================================================================"
