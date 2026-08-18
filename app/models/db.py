"""
[EN]
Postgres connection handling. One connection per request, opened and closed by
the `connection()` context manager — the same lifecycle the app had before,
just no longer written out in every route.

[RU]
Работа с подключением к Postgres. Одно подключение на запрос, открывается и
закрывается контекст-менеджером `connection()` — тот же жизненный цикл, что и
раньше, просто больше не расписан в каждом маршруте.
"""

from contextlib import contextmanager

import psycopg2

from app import config


def get_conn():
    return psycopg2.connect(
        host=config.PG_HOST, port=config.PG_PORT, user=config.PG_USER,
        password=config.pg_password(), dbname=config.PG_DB,
    )


@contextmanager
def connection():
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()
