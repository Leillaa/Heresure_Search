-- [EN] Loads staging_licenses.csv (prepared by parser.py) into the main
-- licenses table. Nothing is overwritten or deleted:
--   - within the new batch, removes duplicates (same Full Name + Business Email)
--   - inserts into licenses only agents not already present
--     (compared by the same Full Name + Business Email pair)
-- This protects manually-set checked / "Personal Email" on existing rows
-- from being overwritten when the file is downloaded again.
-- [RU] Загружает staging_licenses.csv (подготовленный parser.py) в основную
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

-- [EN] CLIENT-side psql meta-command: the path is resolved against psql's own
-- working directory, which scripts/parser.py pins with cwd= on the subprocess.
-- Do NOT try to parameterise this with `psql -v` and :'var' — psql performs no
-- variable interpolation inside \copy arguments, so the filename would be taken
-- literally as :'var'.
-- [RU] КЛИЕНТСКАЯ meta-команда psql: путь считается от собственного рабочего
-- каталога psql, который scripts/parser.py фиксирует через cwd= у subprocess.
-- НЕ пытайтесь параметризовать это через `psql -v` и :'var' — psql не подставляет
-- переменные внутрь аргументов \copy, имя файла будет взято буквально как :'var'.
\copy staging_licenses FROM 'staging_licenses.csv' WITH (FORMAT csv, HEADER true)

-- [EN] GROUP BY is itself NULL-safe (NULLs group together), so the in-batch
-- dedup doesn't need IS NOT DISTINCT FROM and works via fast hash
-- aggregation rather than a slow self-join.
-- [RU] GROUP BY сам по себе NULL-safe (NULL-ы группируются вместе), поэтому
-- дедуп внутри пачки не нуждается в IS NOT DISTINCT FROM и работает
-- через быстрое hash-агрегирование, а не медленный self-join.
DELETE FROM staging_licenses
WHERE ctid NOT IN (
    SELECT min(ctid)
    FROM staging_licenses
    GROUP BY "Full Name", "Business Email"
);

-- [EN] COALESCE makes the comparison NULL-safe while staying a plain "=", which
-- the planner can execute as a hash anti join instead of a nested loop.
-- [RU] COALESCE делает сравнение NULL-safe, оставаясь обычным "=", которое
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
