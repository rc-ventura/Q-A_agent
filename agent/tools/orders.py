import json
import sqlite3
import unicodedata

from langchain_core.tools import tool

from agent.tools.db import open_readonly


def _norm(text: str | None) -> str:
    """Minusculas sem acentos para match tolerante de nome."""
    return unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()


def _open(db_path):
    """Abre a base read-only; ausente degrada com erro explicito."""
    return open_readonly(db_path)


def make_orders_tools(db_path: str) -> list:
    """Tools de pedidos fechados sobre o SQLite operacional (read-only)."""

    @tool
    def find_customer(name: str | None = None, email: str | None = None) -> str:
        """Identifica o cliente pelo nome e/ou e-mail ANTES de expor pedidos.

        Busca por parte do nome (ignora caixa e acentos) ou e-mail exato.
        Retorna {"matches": [{customer_id, name, city}]} — nunca inclui
        e-mail/telefone do cliente (minimização LGPD). 0 candidatos ou
        vários candidatos exigem esclarecimento, nunca chute. Chame com
        ao menos um dos identificadores.
        """
        if not name and not email:
            return json.dumps({"error": "missing_identifier"})
        try:
            conn = _open(db_path)
        except sqlite3.Error as exc:
            return json.dumps({"error": "store_unavailable", "detail": str(exc)}, ensure_ascii=False)
        try:
            rows = conn.execute(
                "SELECT customer_id, name, email, city FROM customers"
            ).fetchall()
        finally:
            conn.close()
        q_name, q_email = _norm(name), _norm(email)
        matches = [
            {"customer_id": r["customer_id"], "name": r["name"], "city": r["city"]}
            for r in rows
            if (q_name and q_name in _norm(r["name"]))
            or (q_email and q_email == _norm(r["email"]))
        ]
        return json.dumps({"matches": matches}, ensure_ascii=False)

    @tool
    def list_customer_orders(customer_id: int) -> str:
        """Lista os pedidos de um cliente já identificado por find_customer.

        Cada pedido traz order_id, status, order_date, total_brl,
        payment_method e items ([{name, quantity}] com nome e quantidade de cada produto). tracking_code e
        estimated_delivery aparecem só quando existem; cancelled traz o
        motivo em notes quando houver. Retorna {"orders": [...]}.
        """
        try:
            conn = _open(db_path)
        except sqlite3.Error as exc:
            return json.dumps({"error": "store_unavailable", "detail": str(exc)}, ensure_ascii=False)
        try:
            orders = conn.execute(
                "SELECT order_id, status, order_date, total_brl, payment_method,"
                "       tracking_code, estimated_delivery, notes"
                " FROM orders WHERE customer_id = ? ORDER BY order_date DESC",
                (customer_id,),
            ).fetchall()
            items = conn.execute(
                "SELECT oi.order_id, p.name, oi.quantity FROM order_items oi"
                " JOIN products p ON p.product_id = oi.product_id"
                " WHERE oi.order_id IN (SELECT order_id FROM orders WHERE customer_id = ?)",
                (customer_id,),
            ).fetchall()
        finally:
            conn.close()
        items_by_order: dict[int, list[dict]] = {}
        for it in items:
            items_by_order.setdefault(it["order_id"], []).append(
                {"name": it["name"], "quantity": it["quantity"]}
            )
        result = []
        for o in orders:
            entry = {
                "order_id": o["order_id"],
                "status": o["status"],
                "order_date": o["order_date"],
                "total_brl": o["total_brl"],
                "payment_method": o["payment_method"],
                "items": items_by_order.get(o["order_id"], []),
            }
            if o["tracking_code"]:
                entry["tracking_code"] = o["tracking_code"]
            if o["estimated_delivery"]:
                entry["estimated_delivery"] = o["estimated_delivery"]
            if o["notes"]:
                entry["notes"] = o["notes"]
            result.append(entry)
        return json.dumps({"orders": result}, ensure_ascii=False)

    return [find_customer, list_customer_orders]
