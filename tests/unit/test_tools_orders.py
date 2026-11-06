import json
import sqlite3

import pytest

from agent.ingest import ingest_all
from agent.settings import Settings
from agent.tools.orders import make_orders_tools


@pytest.fixture(scope="module")
def tools(tmp_path_factory):
    path = tmp_path_factory.mktemp("db") / "store.db"
    conn = sqlite3.connect(path)
    ingest_all(Settings().source_dir, conn)
    conn.close()
    return {t.name: t for t in make_orders_tools(str(path))}


def _run(tool, **kwargs):
    return json.loads(tool.invoke(kwargs))


def test_find_customer_exact_name_lgpd(tools):
    res = _run(tools["find_customer"], name="Pedro Henrique Oliveira")
    assert len(res["matches"]) == 1
    m = res["matches"][0]
    assert m["customer_id"] == 3
    assert set(m.keys()) <= {"customer_id", "name", "city"}  # sem email/telefone


def test_find_customer_ambiguous(tools):
    res = _run(tools["find_customer"], name="Pedro")
    assert len(res["matches"]) >= 2


def test_find_customer_by_email(tools):
    res = _run(tools["find_customer"], email="pedro.oliveira@jmail.com")
    assert res["matches"][0]["customer_id"] == 3


def test_find_customer_missing_identifier(tools):
    res = _run(tools["find_customer"])
    assert res["error"] == "missing_identifier"


def test_find_customer_no_match(tools):
    res = _run(tools["find_customer"], name="Zezinho Inexistente")
    assert res == {"matches": []}


def test_orders_delivered_and_cancelled(tools):
    res = _run(tools["list_customer_orders"], customer_id=3)
    by_id = {o["order_id"]: o for o in res["orders"]}
    delivered = by_id[1]
    assert delivered["status"] == "entregue"
    assert delivered["tracking_code"] == "BRAB1234567BR"
    assert delivered["estimated_delivery"]
    cancelled = by_id[19]
    assert cancelled["status"] == "cancelado"
    assert "Pagamento não confirmado" in cancelled["notes"]
    assert "tracking_code" not in cancelled  # vazio nao aparece


def test_orders_include_item_names_and_quantities(tools):
    res = _run(tools["list_customer_orders"], customer_id=3)
    by_id = {o["order_id"]: o for o in res["orders"]}
    assert by_id[1]["items"] == [{"name": "Martin D-28 Dreadnought Natural", "quantity": 1}]
    assert by_id[19]["items"] == [{"name": "Taylor 214ce Elétrico Aço Natural", "quantity": 1}]


def test_orders_quantity_reflects_more_than_one_unit(tools):
    res = _run(tools["list_customer_orders"], customer_id=12)
    order = next(o for o in res["orders"] if o["order_id"] == 3)
    assert order["items"][0]["quantity"] == 2


def test_orders_unknown_customer(tools):
    res = _run(tools["list_customer_orders"], customer_id=99999)
    assert res == {"orders": []}


@pytest.mark.parametrize(
    "customer_id,order_id,status,payment",
    [
        (2, 8, "enviado", "cartão de débito"),
        (3, 1, "entregue", "PIX"),
        (12, 3, "entregue", "cartão de crédito em 12x"),
        (8, 13, "aguardando pagamento", "PIX"),
        (4, 11, "confirmado", "boleto"),
    ],
)
def test_orders_status_and_payment_in_portuguese(tools, customer_id, order_id, status, payment):
    """O cliente nunca deve ver os codigos internos (shipped, credit_12x)."""
    res = _run(tools["list_customer_orders"], customer_id=customer_id)
    order = next(o for o in res["orders"] if o["order_id"] == order_id)
    assert order["status"] == status
    assert order["payment_method"] == payment


def test_orders_items_not_duplicated_after_reingest(tmp_path):
    path = tmp_path / "store.db"
    conn = sqlite3.connect(path)
    ingest_all(Settings().source_dir, conn)
    ingest_all(Settings().source_dir, conn)
    conn.close()
    tool = {t.name: t for t in make_orders_tools(str(path))}["list_customer_orders"]
    order = next(o for o in _run(tool, customer_id=2)["orders"] if o["order_id"] == 8)
    assert order["items"] == [{"name": order["items"][0]["name"], "quantity": 1}]
