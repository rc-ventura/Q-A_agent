import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories(
  category_id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT);
CREATE TABLE IF NOT EXISTS customers(
  customer_id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT, email TEXT, city TEXT);
CREATE TABLE IF NOT EXISTS products(
  product_id INTEGER PRIMARY KEY, name TEXT NOT NULL,
  category_id INTEGER REFERENCES categories(category_id),
  price_brl REAL NOT NULL CHECK(price_brl >= 0), description TEXT,
  stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK(stock_quantity >= 0),
  status TEXT NOT NULL, specs TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS orders(
  order_id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers(customer_id),
  order_date TEXT, status TEXT NOT NULL, total_brl REAL, payment_method TEXT,
  tracking_code TEXT, estimated_delivery TEXT, notes TEXT);
CREATE TABLE IF NOT EXISTS order_items(
  order_id INTEGER REFERENCES orders(order_id), product_id INTEGER REFERENCES products(product_id),
  quantity INTEGER NOT NULL CHECK(quantity > 0));
CREATE TABLE IF NOT EXISTS promotions(
  promotion_id INTEGER PRIMARY KEY, product_id INTEGER REFERENCES products(product_id),
  discount_percent REAL CHECK(discount_percent BETWEEN 0 AND 100),
  description TEXT, is_active INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_promos_product ON promotions(product_id);
"""


def init_schema(conn: sqlite3.Connection) -> None:
    """Cria o schema SQLite (idempotente) com constraints de integridade."""
    conn.executescript(SCHEMA)
    conn.executescript(ACTIVE_PROMOTIONS_VIEW)


def connect_readonly(path) -> sqlite3.Connection:
    """Abre conexao read-only (tools nunca escrevem no operacional)."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


ACTIVE_PROMOTIONS_VIEW = """
CREATE VIEW IF NOT EXISTS v_active_promotions AS
SELECT p.product_id, p.name, p.price_brl, pr.discount_percent,
       round(p.price_brl * (1 - pr.discount_percent / 100.0), 2) AS final_price_brl,
       pr.description AS promotion_description
FROM products p
JOIN promotions pr ON pr.product_id = p.product_id
WHERE pr.is_active = 1;
"""


def create_views(conn: sqlite3.Connection) -> None:
    """Cria a view de promocoes ativas (preco final calculado no SQL)."""
    conn.executescript(ACTIVE_PROMOTIONS_VIEW)
