-- Удаляет дубли из licenses: строка считается дублем другой, если у них
-- совпадают одновременно "Full Name" и "Business Email".
-- Если хотя бы одно из этих двух полей отличается — строки НЕ трогаем.
-- Из каждой группы дублей оставляем запись с наименьшим id (самую первую).

BEGIN;

-- GROUP BY сам по себе NULL-safe и использует быстрое hash-агрегирование
-- вместо медленного self-join с IS NOT DISTINCT FROM.
DELETE FROM licenses
WHERE id NOT IN (
    SELECT min(id)
    FROM licenses
    GROUP BY "Full Name", "Business Email"
);

COMMIT;
