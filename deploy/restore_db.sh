#!/usr/bin/env bash
# Запускать НА СЕРВЕРЕ после того, как provision.sh создал роль и пустую
# базу, а дамп (из deploy/dump_db.sh) уже залит на сервер (scp).
#
# Использование:
#   PGPASSWORD=... ./deploy/restore_db.sh /root/agents_heresure_XXXXXXXX_XXXXXX.dump
# Переменные можно переопределить: PGHOST/PGPORT/PGUSER/PGDATABASE

set -euo pipefail

DUMP_FILE="${1:?Использование: $0 путь_к_файлу.dump}"
[ -f "$DUMP_FILE" ] || { echo "Файл не найден: $DUMP_FILE" >&2; exit 1; }

PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-agents_app}"
PGDATABASE="${PGDATABASE:-Agents_Heresure}"

: "${PGPASSWORD:?Задай PGPASSWORD (пароль роли $PGUSER в Postgres на сервере)}"
export PGPASSWORD

echo "==> Восстанавливаю $DUMP_FILE -> $PGDATABASE@$PGHOST (роль $PGUSER)"
# -c --if-exists: сначала дропает существующие объекты (если скрипт запускают
# повторно), --no-owner: не пытается назначить владельцем роль из дампа
# (obычно 'postgres' с локальной машины), а использует текущего пользователя.
pg_restore -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  --no-owner --role="$PGUSER" -c --if-exists "$DUMP_FILE"

echo "==> Готово. Проверка количества строк:"
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c 'SELECT COUNT(*) FROM licenses;'
