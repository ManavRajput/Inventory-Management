PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    sku TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    variety TEXT,
    price REAL NOT NULL CHECK (price >= 0),
    quantity REAL NOT NULL CHECK (quantity >= 0),
    attributes TEXT DEFAULT '{}',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_products_name ON products (name);
CREATE INDEX IF NOT EXISTS idx_products_variety ON products (variety);

CREATE TABLE IF NOT EXISTS stock_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    movement TEXT NOT NULL CHECK (movement IN ('IN','OUT','ADJUST')),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL,
    source TEXT,
    ref_id TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ledger_product ON stock_ledger (product_id);
CREATE INDEX IF NOT EXISTS idx_ledger_movement ON stock_ledger (movement);
CREATE INDEX IF NOT EXISTS idx_ledger_created ON stock_ledger (created_at);

-- Emulate view via regular view (SQLite supports CREATE VIEW)
DROP VIEW IF EXISTS stock_view;
CREATE VIEW stock_view AS
SELECT
    p.id AS product_id,
    COALESCE(SUM(CASE l.movement
        WHEN 'IN' THEN l.quantity
        WHEN 'OUT' THEN -l.quantity
        WHEN 'ADJUST' THEN l.quantity
    END), 0) AS current_quantity
FROM products p
LEFT JOIN stock_ledger l ON l.product_id = p.id
GROUP BY p.id;

-- Update updated_at via trigger
DROP TRIGGER IF EXISTS trg_products_updated_at;
CREATE TRIGGER trg_products_updated_at
AFTER UPDATE ON products
FOR EACH ROW
BEGIN
  UPDATE products SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;
