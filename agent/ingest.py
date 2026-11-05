import csv
import sqlite3
from pathlib import Path

from agent.db import init_schema
from agent.models import Category, Customer, Order, OrderItem, Product, Promotion

_INSERTS = {
    "categories": ("categories", Category, ["category_id", "name", "description"]),
    "customers": ("customers", Customer, ["customer_id", "name", "phone", "email", "city"]),
    "products": ("products", Product,
                 ["product_id", "name", "category_id", "price_brl", "description",
                  "stock_quantity", "status", "specs", "created_at"]),
    "orders": ("orders", Order,
               ["order_id", "customer_id", "order_date", "status", "total_brl",
                "payment_method", "tracking_code", "estimated_delivery", "notes"]),
    "order_items": ("order_items", OrderItem, ["order_id", "product_id", "quantity"]),
    "promotions": ("promotions", Promotion,
                   ["promotion_id", "product_id", "discount_percent", "description", "is_active"]),
}


def ingest_all(source_dir: Path, conn: sqlite3.Connection) -> dict[str, int]:
    """Carrega os CSVs fonte para o SQLite, validando cada linha via Pydantic.

    Le na ordem de dependencia FK (categorias → produtos → pedidos), aplica
    coercao de tipos (is_active 0/1 → bool) e devolve contagens por tabela.
    """
    init_schema(conn)
    counts: dict[str, int] = {}
    for name, (table, model, cols) in _INSERTS.items():
        with open(source_dir / f"{name}.csv", newline="", encoding="utf-8") as fh:
            rows = [model.model_validate(r).model_dump() for r in csv.DictReader(fh)]
        for r in rows:
            if table == "promotions":
                r["is_active"] = int(bool(r["is_active"]))
            elif table == "orders" and "total_brl" in r:
                r["total_brl"] = r["total_brl"]
        conn.executemany(
            f"INSERT OR REPLACE INTO {table} ({','.join(cols)})"
            f" VALUES ({','.join('?' for _ in cols)})",
            [tuple(r[c] for c in cols) for r in rows],
        )
        counts[table] = len(rows)
    conn.commit()
    return counts
