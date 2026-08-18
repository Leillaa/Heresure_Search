"""
[EN]
Single source of configuration for the whole project — the web app and the
scripts in scripts/ all read their settings from here.

Values come from the .env in the PROJECT ROOT (see .env.example). Real
environment variables always win over .env, so systemd EnvironmentFile= and
docker-compose environment: override the file without any extra wiring.

[RU]
Единый источник конфигурации для всего проекта — и веб-приложение, и скрипты
из scripts/ берут настройки отсюда.

Значения читаются из .env в КОРНЕ ПРОЕКТА (см. .env.example). Реальные
переменные окружения всегда важнее .env, поэтому systemd EnvironmentFile= и
docker-compose environment: переопределяют файл без дополнительной настройки.
"""

import os
from pathlib import Path

# [EN] app/config.py -> the repo root is one level up. resolve() so a symlinked
# checkout or a relative `python -m` invocation still lands on the real root.
# [RU] app/config.py -> корень репозитория на уровень выше. resolve(), чтобы
# симлинк-чекаут или относительный запуск `python -m` всё равно попадал в
# настоящий корень.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"


def load_env(path: Path) -> None:
    """Simple .env parser — no third-party dependencies (like the other
    scripts in this project). Does not overwrite variables already set in
    the environment (e.g. systemd Environment=/EnvironmentFile=).

    Простой парсер .env — без сторонних зависимостей (как в остальных
    скриптах проекта). Не перезаписывает переменные, уже выставленные
    в окружении (например, systemd Environment=/EnvironmentFile=)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Variable {name} is not set (check .env)")
    return value


# [EN] Loaded once, at import — every constant below is read AFTER this line,
# so .env is authoritative for all of them.
# [RU] Загружается один раз, при импорте — все константы ниже читаются ПОСЛЕ
# этой строки, поэтому .env действует на каждую из них.
load_env(ENV_FILE)

PG_BIN = os.environ.get("PG_BIN", "psql")
PG_HOST = os.environ.get("PGHOST", "localhost")
PG_PORT = os.environ.get("PGPORT", "5432")
PG_USER = os.environ.get("PGUSER", "postgres")
PG_DB = os.environ.get("PGDATABASE", "Agents_Heresure")


def pg_password() -> str:
    """[EN] Read on demand, not at import: send_test_email.py needs this module
    for SMTP settings but never touches Postgres, and must not be blocked by a
    missing PGPASSWORD. The web app calls this in create_app() so gunicorn
    still refuses to boot rather than failing on the first request.

    [RU] Читается по требованию, а не при импорте: send_test_email.py берёт
    отсюда SMTP-настройки, но с Postgres не работает, и отсутствие PGPASSWORD
    не должно его блокировать. Веб-приложение вызывает это в create_app(),
    поэтому gunicorn по-прежнему не стартует, а не падает на первом запросе."""
    return get_required("PGPASSWORD")


# [EN] HTTP Basic Auth — on the server the database holds real names/emails/phones,
# access is team-only. Format in .env: BASIC_AUTH_USERS=user1:pass1,user2:pass2
# If the variable is unset, auth is disabled (for local development).
# [RU] HTTP Basic Auth — на сервере в базе реальные ФИО/email/телефоны, доступ
# только для команды. Формат в .env: BASIC_AUTH_USERS=user1:pass1,user2:pass2
# Если переменная не задана — auth выключена (для локальной разработки).
_raw_users = os.environ.get("BASIC_AUTH_USERS", "")
BASIC_AUTH_USERS = dict(
    pair.split(":", 1) for pair in _raw_users.split(",") if ":" in pair
)

PAGE_SIZE = 50
