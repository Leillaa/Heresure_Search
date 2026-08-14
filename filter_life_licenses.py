"""
Фильтрует AllValidLicensesIndividual.csv и сохраняет в текстовый файл
записи людей, у которых одновременно:
  - Mailing State == FL
  - Mailing City относится к Broward County или Miami-Dade County
  - License TYCL Desc относится к life / life & health (включая annuity-варианты)
"""

import csv
from pathlib import Path

INPUT = Path("AllValidLicensesIndividual.csv")
OUTPUT = Path("life_licenses_broward_miamidade.txt")

# License TYCL Desc, которые считаем "life" / "life and health"
LIFE_DESCS = {
    "LIFE",
    "LIFE & HEALTH",
    "LIFE INCL VAR ANNUITY & HEALTH",
    "LIFE INCL VARIABLE ANNUITY",
}

# Официальные муниципалитеты Broward County + распространённые написания
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

# Официальные муниципалитеты Miami-Dade County + распространённые написания
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


def clean(value) -> str:
    """Убирает Excel-экранирование вида ="12345" -> 12345."""
    value = (value or "").strip()
    if value.startswith('="') and value.endswith('"'):
        value = value[2:-1]
    return value


def main() -> None:
    matched = 0
    total = 0

    with INPUT.open(newline="", encoding="utf-8", errors="replace") as fin, \
         OUTPUT.open("w", encoding="utf-8") as fout:

        reader = csv.DictReader(fin)

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
            fout.write("=" * 70 + "\n")
            for key, value in row.items():
                if key is None:
                    continue  # лишние поля в строке (кривой CSV), пропускаем
                fout.write(f"{key}: {clean(value)}\n")
            fout.write("\n")

            if total % 200_000 == 0:
                print(f"...обработано {total} строк, найдено {matched}")

    print(f"Готово. Всего строк: {total}. Подошло под условия: {matched}.")
    print(f"Результат сохранён в {OUTPUT.resolve()}")


if __name__ == "__main__":
    main()
