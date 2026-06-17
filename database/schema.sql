CREATE TABLE IF NOT EXISTS medicines (
    id                  TEXT PRIMARY KEY,
    source              TEXT NOT NULL,
    url                 TEXT UNIQUE NOT NULL,
    name                TEXT,
    active_ingredient   TEXT,
    drug_class          TEXT,
    indication          TEXT,
    dosage              TEXT,
    adverse_effect      TEXT,
    contraindication    TEXT,
    description         TEXT,
    scraped_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_source   ON medicines(source);
CREATE INDEX IF NOT EXISTS idx_name     ON medicines(name);