#!/usr/bin/env bash
# Запускать ЛОКАЛЬНО (у себя на маке). Делает дамп текущей локальной базы
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

: "${PGPASSWORD:?Не задан PGPASSWORD (проверь .env или экспортируй переменную)}"
export PGPASSWORD

OUT="agents_heresure_$(date +%Y%m%d_%H%M%S).dump"

echo "==> Дамплю $PGDATABASE@$PGHOST:$PGPORT -> $OUT"
"$PG_DUMP_BIN" -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -Fc -f "$OUT"

echo "==> Готово: $OUT ($(du -h "$OUT" | cut -f1))"
echo
echo "Дальше залей файл на сервер, например:"
echo "  scp $OUT root@<IP_ДРОПЛЕТА>:/root/"
echo "и на сервере запусти deploy/restore_db.sh с этим файлом."
