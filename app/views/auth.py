"""
[EN]
HTTP Basic Auth for the whole site. On the server the database holds real
names/emails/phones, so access is team-only — see BASIC_AUTH_USERS in
.env.example. With the variable unset, auth is disabled for local development.

[RU]
HTTP Basic Auth для всего сайта. На сервере в базе реальные ФИО/email/телефоны,
поэтому доступ только для команды — см. BASIC_AUTH_USERS в .env.example. Если
переменная не задана, auth выключена для локальной разработки.
"""

import functools
import hmac

from flask import Response, request

from app.config import BASIC_AUTH_USERS


def require_auth(view):
    # [EN] NOTE: this must be applied UNDER the route decorator, i.e.
    #     @bp.route("/")
    #     @require_auth
    # If the order is flipped, the blueprint registers the unwrapped view and
    # auth is silently bypassed — no error, just an open page.
    # [RU] ВАЖНО: применяется ПОД декоратором маршрута, то есть
    #     @bp.route("/")
    #     @require_auth
    # Если порядок перевернуть, blueprint зарегистрирует необёрнутую функцию и
    # auth молча отключится — без ошибки, просто открытая страница.
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not BASIC_AUTH_USERS:
            return view(*args, **kwargs)  # auth not configured (local development) / auth не настроена (локальная разработка)

        auth = request.authorization
        valid = (
            auth
            and auth.username in BASIC_AUTH_USERS
            and hmac.compare_digest(auth.password or "", BASIC_AUTH_USERS[auth.username])
        )
        if not valid:
            return Response(
                "Authorization required.", 401,
                {"WWW-Authenticate": 'Basic realm="Agents_Heresure"'},
            )
        return view(*args, **kwargs)

    return wrapped
