-- Bharat Intelligence Agent — Demo DB Schema
-- Run against your Supabase project via: psql $DATABASE_URL -f 001_schema.sql
-- or via the Supabase SQL editor.

CREATE TABLE IF NOT EXISTS customers (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name        VARCHAR(255) NOT NULL,
  email       VARCHAR(255) UNIQUE NOT NULL,
  phone       VARCHAR(20),
  city        VARCHAR(100),
  gstin       VARCHAR(15),
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name        VARCHAR(255) NOT NULL,
  sku         VARCHAR(50) UNIQUE NOT NULL,
  category    VARCHAR(100),
  price       DECIMAL(12, 2) NOT NULL,
  unit        VARCHAR(20) DEFAULT 'piece',
  description TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orders (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id    UUID        NOT NULL REFERENCES customers(id),
  status         VARCHAR(50) NOT NULL DEFAULT 'pending',   -- pending | completed | cancelled | delivered
  total_amount   DECIMAL(12, 2) NOT NULL,
  payment_status VARCHAR(50) DEFAULT 'unpaid',             -- unpaid | paid | partial
  order_date     TIMESTAMPTZ DEFAULT NOW(),
  delivery_date  TIMESTAMPTZ,
  notes          TEXT,
  created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_items (
  id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id    UUID    NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id  UUID    NOT NULL REFERENCES products(id),
  quantity    INTEGER NOT NULL CHECK (quantity > 0),
  unit_price  DECIMAL(12, 2) NOT NULL,
  total_price DECIMAL(12, 2) GENERATED ALWAYS AS (quantity * unit_price) STORED
);

CREATE TABLE IF NOT EXISTS inventory (
  id               UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id       UUID    NOT NULL REFERENCES products(id) UNIQUE,
  quantity_on_hand INTEGER NOT NULL DEFAULT 0,
  reorder_level    INTEGER DEFAULT 10,
  last_restocked_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent query history — persisted for the frontend history tab
CREATE TABLE IF NOT EXISTS query_history (
  id             BIGSERIAL   PRIMARY KEY,
  session_id     VARCHAR(100),
  user_message   TEXT        NOT NULL,
  sql_generated  TEXT,
  result_summary TEXT,
  sources_used   TEXT[]      DEFAULT '{}',
  chart_url      TEXT,
  created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_orders_customer_id  ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status       ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_date         ON orders(order_date DESC);
CREATE INDEX IF NOT EXISTS idx_orders_payment      ON orders(payment_status);
CREATE INDEX IF NOT EXISTS idx_items_order_id      ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_items_product_id    ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_history_created     ON query_history(created_at DESC);
