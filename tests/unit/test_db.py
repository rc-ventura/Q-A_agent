import sqlite3

import pytest

from agent.db import connect_readonly, init_schema


@pytest.mark.parametrize("folder", ["proj#2", "100%", "a?b", "com espaco"])
def test_connect_readonly_handles_special_characters_in_path(tmp_path, folder):
    path = tmp_path / folder / "store.db"
    path.parent.mkdir()
    conn = sqlite3.connect(path)
    init_schema(conn)
    conn.close()
    ro = connect_readonly(path)
    try:
        assert ro.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0
        with pytest.raises(sqlite3.OperationalError):
            ro.execute("INSERT INTO categories(category_id, name) VALUES (1, 'x')")
    finally:
        ro.close()


def test_active_promotions_view_has_one_row_per_product_with_best_discount():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    conn.execute("INSERT INTO categories VALUES (1, 'Violões', NULL)")
    conn.execute(
        "INSERT INTO products VALUES (1, 'Violão X', 1, 1000, NULL, 3, 'active', NULL, NULL)"
    )
    conn.executemany(
        "INSERT INTO promotions VALUES (?, 1, ?, ?, ?)",
        [(1, 10, "Menor", 1), (2, 30, "Maior", 1), (3, 50, "Inativa", 0), (4, 30, "Empate", 1)],
    )
    rows = conn.execute("SELECT discount_percent, promotion_description FROM v_active_promotions").fetchall()
    assert rows == [(30.0, "Maior")]


def test_init_schema_refreshes_a_stale_view():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    conn.execute("DROP VIEW v_active_promotions")
    conn.execute(
        "CREATE VIEW v_active_promotions AS SELECT p.product_id, p.name, p.price_brl,"
        " 0 AS discount_percent, p.price_brl AS final_price_brl, '' AS promotion_description FROM products p"
    )
    init_schema(conn)
    sql = conn.execute("SELECT sql FROM sqlite_master WHERE name='v_active_promotions'").fetchone()[0]
    assert "MAX" in sql.upper() or "LIMIT 1" in sql.upper()
