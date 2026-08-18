"""
[EN]
Data access for the `licenses` table. Every SQL statement the web app runs
lives here — controllers ask for data, they don't write queries.

[RU]
Доступ к данным таблицы `licenses`. Все SQL-запросы веб-приложения живут
здесь — контроллеры запрашивают данные, а не пишут запросы.
"""

import psycopg2.extras

# [EN] Allowlist of status filters. The values below are interpolated into the
# WHERE clause of fetch_page(), so they must NEVER come from user input —
# normalize_status() right underneath is what guarantees that, which is why the
# two live side by side in this module.
# [RU] Белый список фильтров по статусу. Значения ниже подставляются в WHERE
# внутри fetch_page(), поэтому они НИКОГДА не должны приходить от пользователя —
# это гарантирует normalize_status() прямо под ними, поэтому обе части лежат
# рядом в одном модуле.
STATUS_FILTERS = {
    "all": None,
    "checked": "checked = true",
    "unchecked": "checked = false",
}


def normalize_status(status: str) -> str:
    """Maps anything unrecognised back onto "all".
    Приводит любое неизвестное значение к "all"."""
    return status if status in STATUS_FILTERS else "all"


def status_counts(conn) -> tuple[int, int, int]:
    """Returns (all, checked, unchecked) — the three filter-tab numbers at once,
    in a single pass over the table.

    Возвращает (all, checked, unchecked) — сразу три цифры для вкладок фильтра,
    одним проходом по таблице."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*),
                   COUNT(*) FILTER (WHERE checked),
                   COUNT(*) FILTER (WHERE NOT checked)
            FROM licenses;
            """
        )
        return cur.fetchone()


def fetch_page(conn, status: str, limit: int, offset: int) -> list[dict]:
    """One page of rows for the given (already normalized) status.
    Одна страница строк для заданного (уже нормализованного) статуса."""
    where_sql = STATUS_FILTERS[status]

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT "License Number", "Full Name", "NPN Number", "License Type",
                   "Business Email", "Business Phone", "Mailing Address",
                   "Personal Email", checked
            FROM licenses
            {"WHERE " + where_sql if where_sql else ""}
            ORDER BY id
            LIMIT %s OFFSET %s;
            """,
            (limit, offset),
        )
        # [EN] fetchall() inside the cursor scope — the caller gets plain dicts,
        # not a cursor that would be dead once the connection closes.
        # [RU] fetchall() внутри области курсора — вызывающий получает обычные
        # dict-ы, а не курсор, который умрёт после закрытия подключения.
        return cur.fetchall()
