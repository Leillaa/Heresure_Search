"""
Рассылка писем агентам из базы (licenses), у которых checked = False.

Логика:
  1. Берём из БД строки с checked = False (у кого есть Business Email).
  2. Отправляем письма ПО ОДНОМУ — в каждом письме в "To" только один
     адрес, получатель не видит, что письмо ушло ещё куда-то.
  3. Между письмами пауза (защита от спам-фильтров/бана у почтового провайдера).
  4. Сразу после успешной отправки помечаем строку checked = True в БД —
     если скрипт упадёт посередине, повторный запуск не пришлёт письмо
     тем, кому уже ушло.
  5. Жёсткий лимит писем за один запуск (--limit), по умолчанию небольшой,
     чтобы не улететь на тысячи адресов случайно.

SMTP-данные — из .env (см. send_test_email.py).

Запуск:
    python3 send_campaign.py                # до 5 писем (дефолт), пауза 5 сек
    python3 send_campaign.py --limit 20 --delay 8
    python3 send_campaign.py --dry-run       # только показать, кому бы ушло, ничего не отправлять
"""

import argparse
import csv
import io
import os
import smtplib
import ssl
import subprocess
import sys
import time
from email.message import EmailMessage
from pathlib import Path

ENV_FILE = Path(__file__).parent / ".env"

PG_BIN = "/Library/PostgreSQL/14/bin/psql"
PG_HOST = "localhost"
PG_PORT = "5432"
PG_USER = "postgres"
PG_DB = "Agents_Heresure"
PG_PASSWORD = os.environ.get("PGPASSWORD", "1560")

SUBJECT = "Test email"
BODY_TEMPLATE = (
    "Здравствуйте, {name}.\n\n"
    "Это тестовое письмо. Если вы его получили — рассылка настроена верно.\n"
)

DEFAULT_LIMIT = 5
DEFAULT_DELAY = 5.0


def load_env(path: Path) -> None:
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
        raise SystemExit(f"Не задана переменная {name} (проверь .env)")
    return value


def pg_env():
    env = os.environ.copy()
    env["PGPASSWORD"] = PG_PASSWORD
    return env


def fetch_candidates(limit: int):
    """Тянет из БД строки с checked = False, у кого есть Business Email."""
    query = (
        'COPY (SELECT id, "Full Name", "Business Email" FROM licenses '
        'WHERE checked = false '
        '  AND "Business Email" IS NOT NULL '
        '  AND "Business Email" <> \'\' '
        f'ORDER BY id LIMIT {int(limit)}) TO STDOUT WITH (FORMAT csv, HEADER true)'
    )
    result = subprocess.run(
        [PG_BIN, "-h", PG_HOST, "-p", PG_PORT, "-U", PG_USER, "-d", PG_DB, "-c", query],
        env=pg_env(), capture_output=True, text=True, check=True,
    )
    reader = csv.DictReader(io.StringIO(result.stdout))
    return list(reader)


def mark_checked(row_id: str) -> None:
    subprocess.run(
        [PG_BIN, "-h", PG_HOST, "-p", PG_PORT, "-U", PG_USER, "-d", PG_DB,
         "-c", f"UPDATE licenses SET checked = true WHERE id = {int(row_id)};"],
        env=pg_env(), check=True, capture_output=True, text=True,
    )


def send_one(server: smtplib.SMTP, mail_from: str, to_addr: str, name: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = SUBJECT
    msg["From"] = mail_from
    msg["To"] = to_addr
    msg.set_content(BODY_TEMPLATE.format(name=name or "коллега"))
    server.send_message(msg)


def open_smtp(host: str, port: int, user: str, password: str) -> smtplib.SMTP:
    if port == 465:
        context = ssl.create_default_context()
        server = smtplib.SMTP_SSL(host, port, context=context, timeout=30)
    else:
        server = smtplib.SMTP(host, port, timeout=30)
        server.starttls(context=ssl.create_default_context())
    server.login(user, password)
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                         help=f"Максимум писем за один запуск (по умолчанию {DEFAULT_LIMIT})")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                         help=f"Пауза между письмами в секундах (по умолчанию {DEFAULT_DELAY})")
    parser.add_argument("--dry-run", action="store_true",
                         help="Только показать список получателей, ничего не отправлять и не менять БД")
    args = parser.parse_args()

    candidates = fetch_candidates(args.limit)

    if not candidates:
        print("Нет строк с checked = False и заполненным Business Email — отправлять некому.")
        return

    print(f"Найдено кандидатов: {len(candidates)} (лимит {args.limit}).")

    if args.dry_run:
        for row in candidates:
            print(f"  [dry-run] id={row['id']} -> {row['Business Email']} ({row['Full Name']})")
        print("Dry-run: письма не отправлялись, БД не менялась.")
        return

    load_env(ENV_FILE)
    host = get_required("SMTP_HOST")
    port = int(get_required("SMTP_PORT"))
    user = get_required("SMTP_USER")
    password = get_required("SMTP_PASSWORD")
    mail_from = get_required("MAIL_FROM")

    server = open_smtp(host, port, user, password)

    sent = 0
    failed = 0
    try:
        for i, row in enumerate(candidates):
            to_addr = row["Business Email"]
            name = row["Full Name"]
            row_id = row["id"]

            try:
                send_one(server, mail_from, to_addr, name)
                mark_checked(row_id)
                sent += 1
                print(f"  [{i+1}/{len(candidates)}] отправлено -> {to_addr}")
            except Exception as exc:
                failed += 1
                print(f"  [{i+1}/{len(candidates)}] ОШИБКА для {to_addr}: {exc}", file=sys.stderr)

            if i < len(candidates) - 1:
                time.sleep(args.delay)
    finally:
        try:
            server.quit()
        except Exception:
            pass

    print(f"Готово. Отправлено: {sent}. Ошибок: {failed}.")


if __name__ == "__main__":
    main()
