import sqlite3


def effective_price_brl(price_brl: float, discount_percent: float) -> float:
    """Preco final com desconto aplicado (arredondado em centavos)."""
    return round(price_brl * (1 - discount_percent / 100), 2)


def max_active_discount(conn: sqlite3.Connection) -> dict[int, float]:
    """Maior desconto ATIVO por produto: {product_id: percent}."""
    rows = conn.execute(
        "SELECT product_id, MAX(discount_percent) FROM promotions"
        " WHERE is_active = 1 GROUP BY product_id"
    ).fetchall()
    return {r[0]: float(r[1]) for r in rows}
