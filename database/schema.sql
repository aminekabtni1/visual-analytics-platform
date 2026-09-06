-- ============================================================
-- Visual Analytics Platform — Relational Schema
-- SQLite compatible (also runs on Postgres with minimal changes)
-- Two logical schemas: RAW (operational) + MINING (analytical results)
-- Every mining run is traceable via mining_runs(run_id)
-- ============================================================

PRAGMA foreign_keys = ON;

-- ── RAW SCHEMA ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS customers (
    customer_id     TEXT PRIMARY KEY,          -- original UCI CustomerID or synthetic
    country         TEXT,
    first_seen      TEXT,                       -- ISO date of first transaction
    last_seen       TEXT
);

CREATE TABLE IF NOT EXISTS products (
    product_id      TEXT PRIMARY KEY,          -- StockCode
    description     TEXT NOT NULL,
    category        TEXT,                       -- derived from description / provided
    unit_price      REAL
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id  TEXT PRIMARY KEY,          -- InvoiceNo
    customer_id     TEXT REFERENCES customers(customer_id),
    invoice_date    TEXT NOT NULL,             -- ISO 8601
    country         TEXT
);

CREATE TABLE IF NOT EXISTS transaction_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id  TEXT NOT NULL REFERENCES transactions(transaction_id) ON DELETE CASCADE,
    product_id      TEXT NOT NULL REFERENCES products(product_id),
    quantity        INTEGER NOT NULL,
    unit_price      REAL NOT NULL,
    line_total      REAL GENERATED ALWAYS AS (quantity * unit_price) STORED,
    UNIQUE(transaction_id, product_id)
);
CREATE INDEX IF NOT EXISTS idx_ti_transaction ON transaction_items(transaction_id);
CREATE INDEX IF NOT EXISTS idx_ti_product ON transaction_items(product_id);
CREATE INDEX IF NOT EXISTS idx_tx_customer ON transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(invoice_date);

-- ── MINING SCHEMA ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS mining_runs (
    run_id          TEXT PRIMARY KEY,          -- uuid
    run_type        TEXT NOT NULL CHECK(run_type IN ('association','clustering','outlier')),
    created_at      TEXT NOT NULL,             -- ISO 8601
    params_json     TEXT NOT NULL,             -- JSON blob of parameters
    notes           TEXT
);

-- Association mining results
CREATE TABLE IF NOT EXISTS frequent_itemsets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL REFERENCES mining_runs(run_id) ON DELETE CASCADE,
    itemset         TEXT NOT NULL,             -- JSON array of product_ids, sorted
    itemset_size    INTEGER NOT NULL,
    support         REAL NOT NULL,
    UNIQUE(run_id, itemset)
);

CREATE TABLE IF NOT EXISTS association_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL REFERENCES mining_runs(run_id) ON DELETE CASCADE,
    antecedent      TEXT NOT NULL,             -- JSON array
    consequent      TEXT NOT NULL,             -- JSON array
    support         REAL NOT NULL,
    confidence      REAL NOT NULL,
    lift            REAL NOT NULL,
    leverage        REAL,
    conviction      REAL,
    UNIQUE(run_id, antecedent, consequent)
);
CREATE INDEX IF NOT EXISTS idx_rules_run ON association_rules(run_id);
CREATE INDEX IF NOT EXISTS idx_fi_run ON frequent_itemsets(run_id);

-- Clustering results
CREATE TABLE IF NOT EXISTS customer_clusters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL REFERENCES mining_runs(run_id) ON DELETE CASCADE,
    cluster_label   INTEGER NOT NULL,
    size            INTEGER NOT NULL,
    avg_recency     REAL,
    avg_frequency   REAL,
    avg_monetary    REAL,
    avg_rfm_score   REAL,
    centroid_json   TEXT,                      -- JSON array [R,F,M] centroid
    UNIQUE(run_id, cluster_label)
);

CREATE TABLE IF NOT EXISTS cluster_assignments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL REFERENCES mining_runs(run_id) ON DELETE CASCADE,
    customer_id     TEXT NOT NULL REFERENCES customers(customer_id),
    cluster_label   INTEGER NOT NULL,
    distance_to_centroid REAL,
    rfm_r           REAL,
    rfm_f           REAL,
    rfm_m           REAL,
    UNIQUE(run_id, customer_id)
);
CREATE INDEX IF NOT EXISTS idx_ca_run ON cluster_assignments(run_id);
CREATE INDEX IF NOT EXISTS idx_ca_customer ON cluster_assignments(customer_id);

-- Outlier detection results
CREATE TABLE IF NOT EXISTS outliers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL REFERENCES mining_runs(run_id) ON DELETE CASCADE,
    transaction_id  TEXT NOT NULL REFERENCES transactions(transaction_id),
    anomaly_score   REAL NOT NULL,             -- Isolation Forest decision score (more negative = more anomalous)
    is_outlier      INTEGER NOT NULL CHECK(is_outlier IN (0,1)),
    reason_json     TEXT,                      -- JSON: contributing features
    UNIQUE(run_id, transaction_id)
);
CREATE INDEX IF NOT EXISTS idx_outliers_run ON outliers(run_id);
