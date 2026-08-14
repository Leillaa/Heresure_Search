-- Загружает staging_licenses.csv (подготовленный parser.py) в основную
-- таблицу licenses. Ничего не перезаписывает и не удаляет:
--   - внутри самой новой пачки убирает дубли (одинаковые Full Name + Business Email)
--   - добавляет в licenses только тех агентов, которых там ещё нет
--     (сравнение по той же паре Full Name + Business Email)
-- Это защищает уже выставленные вручную checked / "Personal Email"
-- у существующих записей от затирания при повторном скачивании файла.

BEGIN;

CREATE TEMP TABLE staging_licenses (
    "License Number"  TEXT,
    "Full Name"       TEXT,
    "NPN Number"      TEXT,
    "License Type"    TEXT,
    "Business Email"  TEXT,
    "Business Phone"  TEXT,
    "Mailing Address" TEXT,
    "Personal Email"  TEXT,
    checked           BOOLEAN
);

\copy staging_licenses FROM 'staging_licenses.csv' WITH (FORMAT csv, HEADER true)

-- GROUP BY сам по себе NULL-safe (NULL-ы группируются вместе), поэтому
-- дедуп внутри пачки не нуждается в IS NOT DISTINCT FROM и работает
-- через быстрое hash-агрегирование, а не медленный self-join.
DELETE FROM staging_licenses
WHERE ctid NOT IN (
    SELECT min(ctid)
    FROM staging_licenses
    GROUP BY "Full Name", "Business Email"
);

-- COALESCE делает сравнение NULL-safe, оставаясь обычным "=", которое
-- планировщик может выполнить hash anti join'ом вместо nested loop.
INSERT INTO licenses (
    "License Number", "Full Name", "NPN Number", "License Type",
    "Business Email", "Business Phone", "Mailing Address",
    "Personal Email", checked
)
SELECT
    s."License Number", s."Full Name", s."NPN Number", s."License Type",
    s."Business Email", s."Business Phone", s."Mailing Address",
    s."Personal Email", s.checked
FROM staging_licenses s
WHERE NOT EXISTS (
    SELECT 1 FROM licenses l
    WHERE COALESCE(l."Full Name", '') = COALESCE(s."Full Name", '')
      AND COALESCE(l."Business Email", '') = COALESCE(s."Business Email", '')
);

COMMIT;
