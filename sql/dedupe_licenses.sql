-- [EN] Removes duplicates from licenses: a row is a duplicate of another if both
-- "Full Name" and "Business Email" match.
-- If at least one of these two fields differs, the rows are NOT touched.
-- From each group of duplicates, keep the row with the smallest id (the earliest).
-- [RU] Удаляет дубли из licenses: строка считается дублем другой, если у них
-- совпадают одновременно "Full Name" и "Business Email".
-- Если хотя бы одно из этих двух полей отличается — строки НЕ трогаем.
-- Из каждой группы дублей оставляем запись с наименьшим id (самую первую).

BEGIN;

-- [EN] GROUP BY is itself NULL-safe and uses fast hash aggregation
-- instead of a slow self-join with IS NOT DISTINCT FROM.
-- [RU] GROUP BY сам по себе NULL-safe и использует быстрое hash-агрегирование
-- вместо медленного self-join с IS NOT DISTINCT FROM.
DELETE FROM licenses
WHERE id NOT IN (
    SELECT min(id)
    FROM licenses
    GROUP BY "Full Name", "Business Email"
);

COMMIT;
