"""
Тестовая отправка одного письма самому себе через SMTP.
Данные берутся из .env в этой же папке (я его не читаю и не логирую —
скрипт сам подгружает переменные во время выполнения).

Нужные переменные в .env:
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=твой_ящик@gmail.com
    SMTP_PASSWORD=пароль_приложения
    MAIL_FROM=твой_ящик@gmail.com
    MAIL_TO=твой_ящик@gmail.com   (для теста можно тот же самый)
"""

import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

ENV_FILE = Path(__file__).parent / ".env"

SUBJECT = "Test email"
BODY = "Это тестовое письмо. Если ты его получил — SMTP настроен верно."


def load_env(path: Path) -> None:
    """Простой парсер .env — без сторонних зависимостей.
    Не перезаписывает переменные, уже выставленные в окружении."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Не задана переменная {name} (проверь .env)")
    return value


def main() -> None:
    load_env(ENV_FILE)

    host = get_required("SMTP_HOST")
    port = int(get_required("SMTP_PORT"))
    user = get_required("SMTP_USER")
    password = get_required("SMTP_PASSWORD")
    mail_from = get_required("MAIL_FROM")
    mail_to = get_required("MAIL_TO")

    msg = EmailMessage()
    msg["Subject"] = SUBJECT
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg.set_content(BODY)

    print(f"Отправляю письмо: {mail_from} -> {mail_to} через {host}:{port} ...")

    try:
        if port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
                server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.starttls(context=ssl.create_default_context())
                server.login(user, password)
                server.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        raise SystemExit(
            "Ошибка авторизации SMTP. Проверь SMTP_USER/SMTP_PASSWORD — "
            "если это Gmail/Yandex/Outlook с 2FA, нужен App Password, "
            "а не обычный пароль от почты."
        )
    except Exception as exc:
        raise SystemExit(f"Ошибка отправки: {exc}")

    print("Готово: письмо отправлено успешно.")


if __name__ == "__main__":
    main()
