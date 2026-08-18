#!/usr/bin/env bash
# [EN] Run LOCALLY (on your own Mac). Dumps the current local Agents_Heresure
# database in Postgres custom format — the most reliable way to transfer
# everything you currently have to the server (schema + all records).
#
# Usage:
#   ./deploy/dump_db.sh
# Variables can be overridden: PGHOST/PGPORT/PGUSER/PGDATABASE/PGPASSWORD
# If there's a .env in the project root, variables are picked up from it automatically.
#
# [RU] Запускать ЛОКАЛЬНО (у себя на маке). Делает дамп текущей локальной базы
# Agents_Heresure в custom-формате Postgres — самый надёжный способ
# перенести на сервер всё, что есть сейчас (схему + все записи).
#
# Использование:
#   ./deploy/dump_db.sh
# Переменные можно переопределить: PGHOST/PGPORT/PGUSER/PGDATABASE/PGPASSWORD
# Если есть .env в корне проекта — переменные подхватятся из него автоматически.

set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source <(grep -v '^\s*#' .env | sed -E 's/^(\w+)=(.*)$/\1=\2/')
  set +a
fi

PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"
PGDATABASE="${PGDATABASE:-Agents_Heresure}"
PG_DUMP_BIN="${PG_DUMP_BIN:-pg_dump}"

: "${PGPASSWORD:?PGPASSWORD is not set (check .env or export the variable)}"
export PGPASSWORD

OUT="agents_heresure_$(date +%Y%m%d_%H%M%S).dump"

echo "==> Dumping $PGDATABASE@$PGHOST:$PGPORT -> $OUT"
"$PG_DUMP_BIN" -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -Fc -f "$OUT"

echo "==> Done: $OUT ($(du -h "$OUT" | cut -f1))"
echo
echo "Next, upload the file to the server, e.g.:"
echo "  scp $OUT root@<DROPLET_IP>:/root/"
echo "and on the server run deploy/restore_db.sh with this file."
