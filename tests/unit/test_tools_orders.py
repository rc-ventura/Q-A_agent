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
    assert delivered["status"] == "delivered"
    assert delivered["tracking_code"] == "BRAB1234567BR"
    assert delivered["estimated_delivery"]
    cancelled = by_id[19]
    assert cancelled["status"] == "cancelled"
    assert "Pagamento não confirmado" in cancelled["notes"]
    assert "tracking_code" not in cancelled  # vazio nao aparece


def test_orders_include_item_names(tools):
    res = _run(tools["list_customer_orders"], customer_id=3)
    assert all(len(o["items"]) >= 1 for o in res["orders"])
    assert all(isinstance(p, str) and p for o in res["orders"] for p in o["items"])


def test_orders_unknown_customer(tools):
    res = _run(tools["list_customer_orders"], customer_id=99999)
    assert res == {"orders": []}
