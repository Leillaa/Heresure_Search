"""
Мини-страница со списком агентов из базы Agents_Heresure.
Постранично (50 на страницу), с кнопкой "Отправить письмо" у каждой
строки — пока кнопка ничего не делает (заглушка под будущую отправку).

Запуск:
    python3 app.py
Открыть в браузере:
    http://127.0.0.1:5000
"""

import os

import psycopg2
import psycopg2.extras
from flask import Flask, render_template_string, request

PG_HOST = "localhost"
PG_PORT = "5432"
PG_USER = "postgres"
PG_DB = "Agents_Heresure"
PG_PASSWORD = os.environ.get("PGPASSWORD", "1560")

PAGE_SIZE = 50

app = Flask(__name__)


def to_tel_href(phone: str) -> str:
    """Готовит tel: ссылку из телефона, чтобы на мобильном по тапу
    предлагалось позвонить."""
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if not digits:
        return ""
    if len(digits) == 10:
        digits = "1" + digits  # добавляем код страны США
    return f"tel:+{digits}"


def get_conn():
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, user=PG_USER,
        password=PG_PASSWORD, dbname=PG_DB,
    )


TEMPLATE = """
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Licenses — Agents_Heresure</title>
<style>
  :root {
    --bg: #f7f7f8;
    --surface: #ffffff;
    --border: #e4e4e7;
    --text: #18181b;
    --text-muted: #71717a;
    --accent: #2563eb;
    --accent-hover: #1d4ed8;
    --badge-true-bg: #dcfce7;
    --badge-true-text: #166534;
    --badge-false-bg: #fef3c7;
    --badge-false-text: #92400e;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
  }
  header {
    padding: 24px 32px 8px;
  }
  h1 {
    font-size: 20px;
    font-weight: 600;
    margin: 0 0 4px;
  }
  .meta {
    color: var(--text-muted);
    font-size: 13px;
  }
  .table-wrap {
    margin: 16px 32px 32px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: auto;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    font-size: 13px;
    min-width: 900px;
  }
  th, td {
    text-align: left;
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    max-width: 260px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  th {
    background: #fafafa;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.03em;
    position: sticky;
    top: 0;
  }
  tbody tr:hover {
    background: #fafafa;
  }
  tbody tr:last-child td {
    border-bottom: none;
  }
  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
  }
  .badge.true { background: var(--badge-true-bg); color: var(--badge-true-text); }
  .badge.false { background: var(--badge-false-bg); color: var(--badge-false-text); }
  .send-btn {
    border: 1px solid var(--accent);
    background: var(--surface);
    color: var(--accent);
    padding: 5px 12px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
  }
  .send-btn:hover {
    background: var(--accent);
    color: #fff;
  }
  .phone-link {
    color: var(--text);
    text-decoration: none;
    border-bottom: 1px dashed var(--text-muted);
  }
  .phone-link:hover {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }
  .pagination {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 0 32px 32px;
  }
  .pagination a, .pagination span.disabled {
    display: inline-flex;
    align-items: center;
    padding: 7px 14px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text);
    text-decoration: none;
    font-size: 13px;
  }
  .pagination a:hover {
    border-color: var(--accent);
    color: var(--accent);
  }
  .pagination span.disabled {
    color: #c4c4c8;
  }
  .pagination .page-info {
    color: var(--text-muted);
    font-size: 13px;
  }
  .toast {
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%) translateY(20px);
    background: #18181b;
    color: #fff;
    padding: 10px 18px;
    border-radius: 8px;
    font-size: 13px;
    opacity: 0;
    transition: opacity 0.2s, transform 0.2s;
    pointer-events: none;
  }
  .toast.show {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
</style>
</head>
<body>
<header>
  <h1>Licenses — Agents_Heresure</h1>
  <div class="meta">Всего записей: {{ total }} · страница {{ page }} из {{ total_pages }}</div>
</header>

<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th>Full Name</th>
        <th>License Type</th>
        <th>Business Email</th>
        <th>Business Phone</th>
        <th>Mailing Address</th>
        <th>Checked</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {% for row in rows %}
      <tr>
        <td title="{{ row['Full Name'] }}">{{ row['Full Name'] }}</td>
        <td title="{{ row['License Type'] }}">{{ row['License Type'] }}</td>
        <td title="{{ row['Business Email'] }}">{{ row['Business Email'] }}</td>
        <td title="{{ row['Business Phone'] }}">
          {% if row['phone_href'] %}
            <a class="phone-link" href="{{ row['phone_href'] }}">{{ row['Business Phone'] }}</a>
          {% else %}
            {{ row['Business Phone'] }}
          {% endif %}
        </td>
        <td title="{{ row['Mailing Address'] }}">{{ row['Mailing Address'] }}</td>
        <td>
          {% if row['checked'] %}
            <span class="badge true">true</span>
          {% else %}
            <span class="badge false">false</span>
          {% endif %}
        </td>
        <td><button class="send-btn" onclick="notReady(this)">Send Email</button></td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<div class="pagination">
  {% if page > 1 %}
    <a href="?page={{ page - 1 }}">&larr; Назад</a>
  {% else %}
    <span class="disabled">&larr; Назад</span>
  {% endif %}

  <span class="page-info">Страница {{ page }} / {{ total_pages }}</span>

  {% if page < total_pages %}
    <a href="?page={{ page + 1 }}">Вперёд &rarr;</a>
  {% else %}
    <span class="disabled">Вперёд &rarr;</span>
  {% endif %}
</div>

<div class="toast" id="toast">Отправка пока не подключена</div>

<script>
function notReady(btn) {
  const toast = document.getElementById('toast');
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 1500);
}
</script>

</body>
</html>
"""


@app.route("/")
def index():
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1

    offset = (page - 1) * PAGE_SIZE

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM licenses;")
            total = cur.fetchone()[0]

        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, total_pages)
        offset = (page - 1) * PAGE_SIZE

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT "License Number", "Full Name", "NPN Number", "License Type",
                       "Business Email", "Business Phone", "Mailing Address",
                       "Personal Email", checked
                FROM licenses
                ORDER BY id
                LIMIT %s OFFSET %s;
                """,
                (PAGE_SIZE, offset),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    for row in rows:
        row["phone_href"] = to_tel_href(row["Business Phone"])

    return render_template_string(
        TEMPLATE, rows=rows, page=page, total_pages=total_pages, total=total,
    )


if __name__ == "__main__":
    # bind только на localhost — в базе реальные персональные данные
    app.run(host="127.0.0.1", port=5000, debug=False)
