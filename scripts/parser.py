"""
[EN]
Downloads the Florida DFS license registry, filters agents by these
conditions:
  - Mailing State == FL
  - Mailing City is in Broward County or Miami-Dade County
  - License TYCL Desc is life / life & health (including annuity variants)
and writes the needed fields straight into Postgres (database
Agents_Heresure, table licenses).

Field transformation rules when writing to the DB:
  - Full Name        = First Name + Middle Name + Last Name (space-separated, no commas/periods)
  - License Type       = License TYCL Desc
  - Mailing Address    = Mailing Address + Mailing Address2 + Mailing City + Mailing State + Mailing Zip
                          (space-separated, empty parts skipped)
  - Business Email     = Email Address
  - Personal Email     = empty (left blank)
  - checked             = always False

Only NEW agents are inserted into licenses (compared by the Full Name +
Business Email pair) — existing rows are not touched, so manually-set
checked / Personal Email values are not overwritten.

[RU]
Скачивает реестр лицензий Florida DFS, фильтрует агентов по условиям:
  - Mailing State == FL
  - Mailing City относится к Broward County или Miami-Dade County
  - License TYCL Desc относится к life / life & health (включая annuity-варианты)
и сразу записывает нужные поля в Postgres (база Agents_Heresure, таблица licenses).

Правила преобразования полей при записи в БД:
  - Full Name        = First Name + Middle Name + Last Name (через пробел, без запятых/точек)
  - License Type       = License TYCL Desc
  - Mailing Address    = Mailing Address + Mailing Address2 + Mailing City + Mailing State + Mailing Zip
                          (через пробел, пустые части пропускаются)
  - Business Email     = Email Address
  - Personal Email     = пусто (не заполняем)
  - checked             = всегда False

В licenses попадают только НОВЫЕ агенты (сравнение по паре Full Name +
Business Email) — уже существующие записи не трогаются, чтобы не затереть
вручную выставленные checked / Personal Email.
"""

import csv
import os
import re
import subprocess
from pathlib import Path

import requests

from app.config import PG_BIN, PG_DB, PG_HOST, PG_PORT, PG_USER, PROJECT_ROOT, pg_password

URL = "https://www.myfloridacfo.com/downloads/AAS/LicenseeSearch/AllValidLicensesIndividual.csv"

# [EN] Anchored to the project root, not the current directory — the script has
# to work the same under systemd (WorkingDirectory=/opt/agent_licence) and from
# a shell in any folder.
# [RU] Привязано к корню проекта, а не к текущему каталогу — скрипт должен
# работать одинаково и под systemd (WorkingDirectory=/opt/agent_licence), и из
# шелла в любой папке.
RAW_CSV = PROJECT_ROOT / "AllValidLicensesIndividual.csv"
STAGING_CSV = PROJECT_ROOT / "staging_licenses.csv"
LOAD_SQL = PROJECT_ROOT / "sql" / "load_script.sql"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
}

# [EN] License TYCL Desc values we treat as "life" / "life and health"
# [RU] License TYCL Desc, которые считаем "life" / "life and health"
LIFE_DESCS = {
    "LIFE",
    "LIFE & HEALTH",
    "LIFE INCL VAR ANNUITY & HEALTH",
    "LIFE INCL VARIABLE ANNUITY",
}

# [EN] Official Broward County municipalities + common spellings
# [RU] Официальные муниципалитеты Broward County + распространённые написания
BROWARD_CITIES = {
    "COCONUT CREEK", "COOPER CITY", "CORAL SPRINGS", "DANIA BEACH", "DAVIE",
    "DEERFIELD BEACH", "FORT LAUDERDALE", "FT LAUDERDALE", "FT. LAUDERDALE",
    "HALLANDALE BEACH", "HALLANDALE", "HILLSBORO BEACH", "HOLLYWOOD",
    "LAUDERDALE BY THE SEA", "LAUDERDALE-BY-THE-SEA", "LAUDERDALE LAKES",
    "LAUDERHILL", "LAZY LAKE", "LIGHTHOUSE POINT", "MARGATE", "MIRAMAR",
    "NORTH LAUDERDALE", "OAKLAND PARK", "PARKLAND", "PEMBROKE PARK",
    "PEMBROKE PINES", "PLANTATION", "POMPANO BEACH", "SEA RANCH LAKES",
    "SOUTHWEST RANCHES", "SUNRISE", "TAMARAC", "WEST PARK", "WESTON",
    "WILTON MANORS",
}

# [EN] Official Miami-Dade County municipalities + common spellings
# [RU] Официальные муниципалитеты Miami-Dade County + распространённые написания
MIAMI_DADE_CITIES = {
    "AVENTURA", "BAL HARBOUR", "BAY HARBOR ISLANDS", "BISCAYNE PARK",
    "CORAL GABLES", "CUTLER BAY", "DORAL", "EL PORTAL", "FLORIDA CITY",
    "GOLDEN BEACH", "HIALEAH", "HIALEAH GARDENS", "HOMESTEAD",
    "INDIAN CREEK", "ISLANDIA", "KEY BISCAYNE", "MEDLEY", "MIAMI",
    "MIAMI BEACH", "MIAMI GARDENS", "MIAMI LAKES", "MIAMI SHORES",
    "MIAMI SPRINGS", "NORTH BAY VILLAGE", "NORTH MIAMI",
    "NORTH MIAMI BEACH", "OPA LOCKA", "OPA-LOCKA", "PALMETTO BAY",
    "PINECREST", "SOUTH MIAMI", "SUNNY ISLES BEACH", "SURFSIDE",
    "SWEETWATER", "VIRGINIA GARDENS", "WEST MIAMI",
}

TARGET_CITIES = BROWARD_CITIES | MIAMI_DADE_CITIES

STAGING_FIELDNAMES = [
    "License Number",
    "Full Name",
    "NPN Number",
    "License Type",
    "Business Email",
    "Business Phone",
    "Mailing Address",
    "Personal Email",
    "checked",
]


def download(dest: Path = RAW_CSV) -> Path:
    print("Downloading Florida DFS individual License...")

    with requests.get(
        URL,
        headers=headers,
        stream=True,
        timeout=(30, 300),
    ) as response:
        response.raise_for_status()

        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0

        with open(dest, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue

                f.write(chunk)
                downloaded += len(chunk)

                if total:
                    percent = downloaded / total * 100
                    print(
                        f"\r{percent:6.2f}% "
                        f"({downloaded / 1024 / 1024:.1f} / "
                        f"{total / 1024 / 1024:.1f} MB)",
                        end="",
                    )
    print(f"\nDone: {dest.resolve()}")
    return dest


def clean(value) -> str:
    """Strips Excel escaping of the form ="12345" -> 12345.
    Убирает Excel-экранирование вида ="12345" -> 12345."""
    value = (value or "").strip()
    if value.startswith('="') and value.endswith('"'):
        value = value[2:-1]
    return value


def clean_name_part(value: str) -> str:
    """Removes commas/periods from a name part, collapses whitespace.
    Убирает запятые/точки из части имени, схлопывает пробелы."""
    value = re.sub(r"[,.]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def build_full_name(row: dict) -> str:
    parts = [
        clean_name_part(clean(row.get("First Name"))),
        clean_name_part(clean(row.get("Middle Name"))),
        clean_name_part(clean(row.get("Last Name"))),
    ]
    return " ".join(p for p in parts if p)


def build_mailing_address(row: dict) -> str:
    parts = [
        clean(row.get("Mailing Address")),
        clean(row.get("Mailing Address2")),
        clean(row.get("Mailing City")),
        clean(row.get("Mailing State")),
        clean(row.get("Mailing Zip")),
    ]
    return " ".join(p for p in parts if p)


def filter_and_transform(csv_path: Path):
    """Streams the source CSV and yields rows already prepared for DB insert.
    Стримит исходный CSV и yield-ит уже готовые для записи в БД строки."""
    total = 0
    matched = 0

    with csv_path.open(newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)

        for row in reader:
            total += 1

            state = clean(row.get("Mailing State")).upper()
            city = clean(row.get("Mailing City")).upper()
            desc = clean(row.get("License TYCL Desc")).upper()

            if state != "FL":
                continue
            if city not in TARGET_CITIES:
                continue
            if desc not in LIFE_DESCS:
                continue

            matched += 1
            yield {
                "License Number": clean(row.get("License Number")),
                "Full Name": build_full_name(row),
                "NPN Number": clean(row.get("NPN Number")),
                "License Type": desc,
                "Business Email": clean(row.get("Email Address")),
                "Business Phone": clean(row.get("Business Phone")),
                "Mailing Address": build_mailing_address(row),
                "Personal Email": "",
                "checked": "false",
            }

            if total % 200_000 == 0:
                print(f"...processed {total} rows, matched {matched}")

    print(f"Filtering done. Total rows: {total}. Matched conditions: {matched}.")


def write_staging_csv(rows, dest: Path = STAGING_CSV) -> int:
    count = 0
    with dest.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=STAGING_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def load_into_postgres() -> None:
    env = os.environ.copy()
    env["PGPASSWORD"] = pg_password()

    before = subprocess.run(
        [PG_BIN, "-h", PG_HOST, "-p", PG_PORT, "-U", PG_USER, "-d", PG_DB,
         "-t", "-c", "SELECT COUNT(*) FROM licenses;"],
        env=env, capture_output=True, text=True, check=True,
    ).stdout.strip()

    subprocess.run(
        [PG_BIN, "-h", PG_HOST, "-p", PG_PORT, "-U", PG_USER, "-d", PG_DB,
         "-f", str(LOAD_SQL)],
        env=env, check=True,
        # [EN] The \copy in sql/load_script.sql is a CLIENT-side psql
        # meta-command: its path is resolved against psql's own CWD, and psql
        # performs NO variable interpolation inside \copy arguments — so the
        # only way to make it CWD-independent is to pin psql's CWD here.
        # [RU] \copy в sql/load_script.sql — КЛИЕНТСКАЯ meta-команда psql: путь
        # считается от собственного CWD psql, и psql НЕ подставляет переменные
        # внутрь аргументов \copy — поэтому единственный способ избавиться от
        # зависимости от CWD это зафиксировать CWD самого psql здесь.
        cwd=STAGING_CSV.parent,
    )

    after = subprocess.run(
        [PG_BIN, "-h", PG_HOST, "-p", PG_PORT, "-U", PG_USER, "-d", PG_DB,
         "-t", "-c", "SELECT COUNT(*) FROM licenses;"],
        env=env, capture_output=True, text=True, check=True,
    ).stdout.strip()

    print(f"Rows before: {before}, after: {after} "
          f"(new rows added: {int(after) - int(before)}).")


def main() -> None:
    csv_path = download()
    rows = filter_and_transform(csv_path)
    count = write_staging_csv(rows)
    print(f"Prepared for load: {count} rows ({STAGING_CSV.resolve()}).")
    load_into_postgres()


if __name__ == "__main__":
    main()
