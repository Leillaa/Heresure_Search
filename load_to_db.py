"""
Парсит life_licenses_broward_miamidade.txt и готовит CSV для загрузки
в таблицу licenses (Postgres, база Agents_Heresure).

Правила преобразования полей:
  - Full Name        = First Name + Middle Name + Last Name (через пробел, без запятых/точек)
  - License Type      = License TYCL Desc
  - Mailing Address    = Mailing Address + Mailing Address2 + Mailing City + Mailing State + Mailing Zip
                         (через пробел, пустые части пропускаются)
  - Business Email     = Email Address
  - Personal Email    = пусто (не заполняем)
  - send_inv           = всегда False
"""

import csv
import re
from pathlib import Path

INPUT = Path("life_licenses_broward_miamidade.txt")
OUTPUT = Path("staging_licenses.csv")

FIELDNAMES = [
    "License Number",
    "Full Name",
    "NPN Number",
    "License Type",
    "Business Email",
    "Business Phone",
    "Mailing Address",
    "Personal Email",
    "send_inv",
]


def parse_blocks(text: str):
    blocks = text.split("=" * 70)
    for block in blocks:
        block = block.strip("\n")
        if not block.strip():
            continue
        record = {}
        for line in block.splitlines():
            if ": " not in line:
                continue
            key, value = line.split(": ", 1)
            record[key.strip()] = value.strip()
        if record:
            yield record


def clean_name_part(value: str) -> str:
    """Убирает запятые/точки из части имени, схлопывает пробелы."""
    value = re.sub(r"[,.]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def build_full_name(record: dict) -> str:
    parts = [
        clean_name_part(record.get("First Name", "")),
        clean_name_part(record.get("Middle Name", "")),
        clean_name_part(record.get("Last Name", "")),
    ]
    return " ".join(p for p in parts if p)


def build_mailing_address(record: dict) -> str:
    parts = [
        record.get("Mailing Address", ""),
        record.get("Mailing Address2", ""),
        record.get("Mailing City", ""),
        record.get("Mailing State", ""),
        record.get("Mailing Zip", ""),
    ]
    return " ".join(p.strip() for p in parts if p and p.strip())


def main() -> None:
    text = INPUT.read_text(encoding="utf-8")

    count = 0
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

        for record in parse_blocks(text):
            writer.writerow({
                "License Number": record.get("License Number", ""),
                "Full Name": build_full_name(record),
                "NPN Number": record.get("NPN Number", ""),
                "License Type": record.get("License TYCL Desc", ""),
                "Business Email": record.get("Email Address", ""),
                "Business Phone": record.get("Business Phone", ""),
                "Mailing Address": build_mailing_address(record),
                "Personal Email": "",
                "send_inv": "false",
            })
            count += 1

    print(f"Готово. Записей подготовлено: {count}")
    print(f"CSV сохранён в {OUTPUT.resolve()}")


if __name__ == "__main__":
    main()
