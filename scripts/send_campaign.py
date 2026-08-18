"""
[EN]
Email campaign to agents from the database (licenses) whose checked = False.

Logic:
  1. Pull rows with checked = False from the DB (those that have a Business Email).
  2. Send emails ONE AT A TIME — each email has only one address in "To",
     the recipient can't see that it went anywhere else.
  3. A pause between emails (protection against spam filters / provider bans).
  4. Immediately after a successful send, mark the row checked = True in the DB —
     if the script crashes midway, a re-run won't email people who were already
     contacted.
  5. A hard cap on emails per run (--limit), small by default, so you don't
     accidentally blast thousands of addresses.

SMTP details — from .env (see send_test_email.py).

Run:
    python3 -m scripts.send_campaign                # up to 5 emails (default), 5 sec pause
    python3 -m scripts.send_campaign --limit 20 --delay 8
    python3 -m scripts.send_campaign --dry-run       # only show who would receive it, send nothing

[RU]
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
    python3 -m scripts.send_campaign                # до 5 писем (дефолт), пауза 5 сек
    python3 -m scripts.send_campaign --limit 20 --delay 8
    python3 -m scripts.send_campaign --dry-run       # только показать, кому бы ушло, ничего не отправлять
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

# [EN] All of these are read in app/config.py AFTER it has loaded .env — which is
# what makes PGHOST/PGPORT/PGUSER/PGDATABASE from .env actually take effect here.
# Before the config was centralised, this module read them at import time, before
# its own load_env() ran in main(), so .env was silently ignored for those four
# and the script always talked to localhost/postgres/Agents_Heresure.
# [RU] Все они читаются в app/config.py ПОСЛЕ загрузки .env — именно поэтому
# PGHOST/PGPORT/PGUSER/PGDATABASE из .env здесь наконец работают. До выноса
# конфига модуль читал их при импорте, ещё до своего load_env() в main(), так что
# .env для этих четырёх молча игнорировался и скрипт всегда шёл на
# localhost/postgres/Agents_Heresure.
from app.config import PG_BIN, PG_DB, PG_HOST, PG_PORT, PG_USER, get_required, pg_password

SUBJECT = "Test email"
BODY_TEMPLATE = (
    "Hello, {name}.\n\n"
    "This is a test email. If you received it, the campaign is configured correctly.\n"
)

DEFAULT_LIMIT = 5
DEFAULT_DELAY = 5.0


def pg_env():
    env = os.environ.copy()
    env["PGPASSWORD"] = pg_password()
    return env


def fetch_candidates(limit: int):
    """Pulls rows with checked = False from the DB that have a Business Email.
    Тянет из БД строки с checked = False, у кого есть Business Email."""
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
    msg.set_content(BODY_TEMPLATE.format(name=name or "colleague"))
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
                         help=f"Max emails per run (default {DEFAULT_LIMIT})")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                         help=f"Pause between emails in seconds (default {DEFAULT_DELAY})")
    parser.add_argument("--dry-run", action="store_true",
                         help="Only show the recipient list, send nothing and don't change the DB")
    args = parser.parse_args()

    # [EN] .env is already loaded by app.config at import; fail here rather than
    # inside the first psql call, so --dry-run also stops early without a password.
    # [RU] .env уже загружен app.config при импорте; падаем здесь, а не внутри
    # первого вызова psql, чтобы и --dry-run останавливался сразу без пароля.
    pg_password()

    candidates = fetch_candidates(args.limit)

    if not candidates:
        print("No rows with checked = False and a filled-in Business Email — no one to send to.")
        return

    print(f"Candidates found: {len(candidates)} (limit {args.limit}).")

    if args.dry_run:
        for row in candidates:
            print(f"  [dry-run] id={row['id']} -> {row['Business Email']} ({row['Full Name']})")
        print("Dry-run: no emails sent, DB unchanged.")
        return

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
                print(f"  [{i+1}/{len(candidates)}] sent -> {to_addr}")
            except Exception as exc:
                failed += 1
                print(f"  [{i+1}/{len(candidates)}] ERROR for {to_addr}: {exc}", file=sys.stderr)

            if i < len(candidates) - 1:
                time.sleep(args.delay)
    finally:
        try:
            server.quit()
        except Exception:
            pass

    print(f"Done. Sent: {sent}. Errors: {failed}.")


if __name__ == "__main__":
    main()
