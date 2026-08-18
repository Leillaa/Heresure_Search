"""
[EN]
The licenses page. Handles the request — query parameters, pagination, choosing
the template — and delegates all SQL to app.models.license.

[RU]
Страница лицензий. Обрабатывает запрос — параметры строки, постраничность,
выбор шаблона — а весь SQL отдаёт в app.models.license.
"""

from flask import Blueprint, render_template, request

from app.config import PAGE_SIZE
from app.models import db, license
from app.views.auth import require_auth

bp = Blueprint("licenses", __name__)


# [EN] Decorator order matters: the route must be the OUTER decorator so the
# blueprint registers the auth-wrapped function. Flipping these silently serves
# the page without auth. / [RU] Порядок декораторов важен: маршрут должен быть
# ВНЕШНИМ, чтобы blueprint зарегистрировал обёрнутую auth-ом функцию. Если
# поменять их местами, страница молча начнёт отдаваться без авторизации.
@bp.route("/")
@require_auth
def index():
    status = license.normalize_status(request.args.get("status", "all"))

    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1

    # [EN] One connection for both queries, so the tab counts and the visible
    # page come from the same snapshot even while send_campaign.py is writing.
    # [RU] Одно подключение на оба запроса, чтобы цифры вкладок и показанная
    # страница брались из одного снимка, даже когда пишет send_campaign.py.
    with db.connection() as conn:
        count_all, count_checked, count_unchecked = license.status_counts(conn)

        total = {
            "all": count_all,
            "checked": count_checked,
            "unchecked": count_unchecked,
        }[status]
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, total_pages)

        rows = license.fetch_page(conn, status, PAGE_SIZE, (page - 1) * PAGE_SIZE)

    return render_template(
        "index.html", rows=rows, page=page, total_pages=total_pages, total=total,
        status=status, count_all=count_all, count_checked=count_checked,
        count_unchecked=count_unchecked,
    )
