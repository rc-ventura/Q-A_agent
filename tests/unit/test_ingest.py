import sqlite3

import pytest

from agent.ingest import ingest_all
from agent.settings import Settings


@pytest.fixture(scope="module")
def conn():
    s = Settings()
    c = sqlite3.connect(":memory:")
    ingest_all(s.source_dir, c)
    yield c
    c.close()


def test_ingest_counts(conn):
    for table, minimum in [
        ("products", 50),
        ("categories", 5),
        ("customers", 10),
        ("orders", 10),
        ("order_items", 10),
        ("promotions", 3),
    ]:
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert n >= minimum, table


def test_fk_integrity(conn):
    orphans = conn.execute(
        "SELECT COUNT(*) FROM order_items oi LEFT JOIN products p ON p.product_id=oi.product_id"
        " WHERE p.product_id IS NULL"
    ).fetchone()[0]
    assert orphans == 0


def test_promotion_logic(conn):
    active = conn.execute(
        "SELECT product_id, price_brl, discount_percent, final_price_brl FROM v_active_promotions"
    ).fetchall()
    assert active
    assert len({r[0] for r in active}) == len(active), "uma promocao por produto"
    for _, price, disc, final in active:
        assert 0 <= disc <= 100
        assert final == round(price * (1 - disc / 100), 2)


def test_orders_join(conn):
    row = conn.execute(
        "SELECT o.order_id, c.name, COUNT(oi.product_id) AS itens, o.total_brl"
        " FROM orders o JOIN customers c ON c.customer_id=o.customer_id"
        " LEFT JOIN order_items oi ON oi.order_id=o.order_id"
        " GROUP BY o.order_id ORDER BY o.order_id LIMIT 1"
    ).fetchone()
    assert row is not None and row[2] >= 1


def test_stock_constraint(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO products(product_id,name,price_brl,stock_quantity,status)"
                     " VALUES (999999,'x',-1,0,'active')")


def test_reingest_is_idempotent():
    """O app reingere a cada start: order_items (sem PK) nao pode duplicar."""
    s = Settings()
    c = sqlite3.connect(":memory:")
    first = ingest_all(s.source_dir, c)
    ingest_all(s.source_dir, c)
    ingest_all(s.source_dir, c)
    for table, expected in first.items():
        assert c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == expected, table
    c.close()
