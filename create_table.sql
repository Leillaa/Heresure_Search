-- Таблица под лицензии агентов
CREATE TABLE IF NOT EXISTS licenses (
    id                BIGSERIAL PRIMARY KEY,
    "License Number"  TEXT,
    "Full Name"       TEXT,
    "NPN Number"      TEXT,
    "License Type"    TEXT,
    "Business Email"  TEXT,
    "Business Phone"  TEXT,
    "Mailing Address" TEXT,
    checked           BOOLEAN NOT NULL DEFAULT FALSE,
    "Personal Email"  TEXT
);
