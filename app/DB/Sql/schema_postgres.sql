CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'movement_type') THEN
        CREATE TYPE movement_type AS ENUM ('IN','OUT','ADJUST');
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    variety TEXT DEFAULT NULL,
    price NUMERIC(12,2) NOT NULL CHECK (price >= 0),
    attributes JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_name ON products (name);
CREATE INDEX IF NOT EXISTS idx_products_variety ON products (variety);

CREATE TABLE IF NOT EXISTS stock_ledger (
    id BIGSERIAL PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    movement movement_type NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12,2),
    source TEXT,
    ref_id TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ledger_product ON stock_ledger (product_id);
CREATE INDEX IF NOT EXISTS idx_ledger_movement ON stock_ledger (movement);
CREATE INDEX IF NOT EXISTS idx_ledger_created ON stock_ledger (created_at);

-- Current stock view
CREATE OR REPLACE VIEW stock_view AS
SELECT
    p.id AS product_id,
    COALESCE(SUM(CASE WHEN l.movement = 'IN' THEN l.quantity
                      WHEN l.movement = 'OUT' THEN -l.quantity
                      WHEN l.movement = 'ADJUST' THEN l.quantity
                 END), 0) AS current_quantity
FROM products p
LEFT JOIN stock_ledger l ON l.product_id = p.id
GROUP BY p.id;

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_products_updated_at ON products;
CREATE TRIGGER trg_products_updated_at
BEFORE UPDATE ON products
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
