"""
[EN]
Application factory. Flask(__name__) here means root_path is this package, so
app/templates/ and app/static/ are discovered with no extra configuration.

[RU]
Фабрика приложения. Flask(__name__) здесь означает, что root_path — это сам
пакет, поэтому app/templates/ и app/static/ находятся без дополнительной
настройки.
"""

from flask import Flask

from app import config
from app.controllers import licenses
from app.views.filters import to_tel_href


def create_app() -> Flask:
    app = Flask(__name__)

    # [EN] Fail at boot, not on the first request — this is what app.py used to
    # get from reading PGPASSWORD at import time.
    # [RU] Падаем при старте, а не на первом запросе — раньше это давало чтение
    # PGPASSWORD во время импорта app.py.
    config.pg_password()

    app.jinja_env.filters["tel_href"] = to_tel_href
    app.register_blueprint(licenses.bp)

    return app
