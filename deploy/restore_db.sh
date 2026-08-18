#!/usr/bin/env bash
# [EN] Run ON THE SERVER after provision.sh created the role and empty
# database, and the dump (from deploy/dump_db.sh) is already uploaded (scp).
#
# Usage:
#   PGPASSWORD=... ./deploy/restore_db.sh /root/agents_heresure_XXXXXXXX_XXXXXX.dump
# Variables can be overridden: PGHOST/PGPORT/PGUSER/PGDATABASE
#
# [RU] Запускать НА СЕРВЕРЕ после того, как provision.sh создал роль и пустую
# базу, а дамп (из deploy/dump_db.sh) уже залит на сервер (scp).
#
# Использование:
#   PGPASSWORD=... ./deploy/restore_db.sh /root/agents_heresure_XXXXXXXX_XXXXXX.dump
# Переменные можно переопределить: PGHOST/PGPORT/PGUSER/PGDATABASE

set -euo pipefail

DUMP_FILE="${1:?Usage: $0 path_to_file.dump}"
[ -f "$DUMP_FILE" ] || { echo "File not found: $DUMP_FILE" >&2; exit 1; }

PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-agents_app}"
PGDATABASE="${PGDATABASE:-Agents_Heresure}"

: "${PGPASSWORD:?Set PGPASSWORD (password for the $PGUSER role in Postgres on the server)}"
export PGPASSWORD

echo "==> Restoring $DUMP_FILE -> $PGDATABASE@$PGHOST (role $PGUSER)"
# [EN] -c --if-exists: first drops existing objects (in case the script is run
# again), --no-owner: doesn't try to set the owner to the role from the dump
# (usually 'postgres' from the local machine), but uses the current user.
# [RU] -c --if-exists: сначала дропает существующие объекты (если скрипт запускают
# повторно), --no-owner: не пытается назначить владельцем роль из дампа
# (обычно 'postgres' с локальной машины), а использует текущего пользователя.
pg_restore -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  --no-owner --role="$PGUSER" -c --if-exists "$DUMP_FILE"

echo "==> Done. Row count check:"
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c 'SELECT COUNT(*) FROM licenses;'
