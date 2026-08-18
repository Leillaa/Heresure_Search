"""
[EN]
Test-send a single email to yourself via SMTP.
Details are read from the .env in this same folder (I don't read or log it —
the script loads the variables itself at runtime).

Required variables in .env:
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=your_mailbox@gmail.com
    SMTP_PASSWORD=app_password
    MAIL_FROM=your_mailbox@gmail.com
    MAIL_TO=your_mailbox@gmail.com   (for a test, the same address is fine)

[RU]
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

import smtplib
import ssl
from email.message import EmailMessage

# [EN] Importing app.config loads .env; this script needs only the SMTP_* values,
# so it must keep working with no PGPASSWORD set — that is why the Postgres
# password is a function in app/config.py rather than a module constant.
# [RU] Импорт app.config загружает .env; этому скрипту нужны только SMTP_*,
# поэтому он должен работать и без PGPASSWORD — именно поэтому пароль Postgres
# в app/config.py оформлен функцией, а не константой модуля.
from app.config import get_required

SUBJECT = "Test email"
BODY = "This is a test email. If you received it, SMTP is configured correctly."


def main() -> None:
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

    print(f"Sending email: {mail_from} -> {mail_to} via {host}:{port} ...")

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
            "SMTP authentication error. Check SMTP_USER/SMTP_PASSWORD — "
            "if this is Gmail/Yandex/Outlook with 2FA, you need an App Password, "
            "not your normal mailbox password."
        )
    except Exception as exc:
        raise SystemExit(f"Send error: {exc}")

    print("Done: email sent successfully.")


if __name__ == "__main__":
    main()
