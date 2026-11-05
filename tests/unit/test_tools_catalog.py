import json
import sqlite3

import pytest

from agent.ingest import ingest_all
from agent.settings import Settings
from agent.tools.catalog import make_catalog_tools


@pytest.fixture(scope="module")
def db_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("db") / "store.db"
    conn = sqlite3.connect(path)
    ingest_all(Settings().source_dir, conn)
    conn.close()
    return str(path)


@pytest.fixture(scope="module")
def tools(db_path):
    return {t.name: t for t in make_catalog_tools(db_path)}


def _run(tool, **kwargs):
    return json.loads(tool.invoke(kwargs))


def test_search_fuzzy_normalized_and_budget(tools):
    res = _run(tools["search_products"], query="violao", max_price_brl=1000)
    assert res, "esperava violoes ate 1000"
    for item in res:
        assert item["category"] == "Violões"
        final = item["active_promotion"]["final_price_brl"] if item["active_promotion"] else item["price_brl"]
        assert final <= 1000
    assert any(item["product_id"] == 81 for item in res), "Yamaha C40 esperada"


def test_active_promotion_only_when_active(tools, db_path):
    res = _run(tools["search_products"], query="", in_stock_only=False, limit=50)
    by_id = {item["product_id"]: item for item in res}
    promo = by_id[127]["active_promotion"]
    assert promo == {"discount_percent": 10, "final_price_brl": 323.1, "campaign": "Oferta Especial"}
    no_promo = [i for i in res if i["active_promotion"] is None]
    assert no_promo, "maioria sem promocao ativa"


def test_details_by_name(tools):
    res = _run(tools["get_product_details"], product_name="Takamine GD20")
    assert res["price_brl"] == 2199.0
    assert res["stock_quantity"] == 5
    assert res["category"] == "Violões"


def test_not_found_suggests(tools):
    res = _run(tools["get_product_details"], product_name="Fender Jagstang")
    assert res["error"] == "not_found"
    assert isinstance(res["did_you_mean"], list) and res["did_you_mean"]


def test_out_of_stock_visibility(tools):
    visible = _run(tools["search_products"], query="Giannini", in_stock_only=False)
    hidden = _run(tools["search_products"], query="Giannini", in_stock_only=True)
    assert any(i["stock_quantity"] == 0 for i in visible)
    assert all(i["stock_quantity"] > 0 for i in hidden)


def test_category_filter(tools):
    res = _run(tools["search_products"], category="Guitarras", limit=10)
    assert res and all(i["category"] == "Guitarras" for i in res)


def test_store_unavailable_is_graceful(tmp_path):
    tools_bad = {t.name: t for t in make_catalog_tools(str(tmp_path / "missing.db"))}
    res = _run(tools_bad["search_products"], query="violao")
    assert res["error"] == "store_unavailable"


def test_details_expose_status_of_discontinued_product(tools):
    details = json.loads(tools["get_product_details"].invoke({"product_name": "Ibanez Bass 2X"}))
    assert details["status"] == "discontinued"
    assert details["price_brl"] == 441.0


def test_search_never_lists_discontinued_products(tools):
    found = json.loads(tools["search_products"].invoke({"query": "Ibanez Bass 2X"}))
    assert found == []


def test_details_status_of_active_product(tools):
    details = json.loads(tools["get_product_details"].invoke({"product_name": "Takamine GD20"}))
    assert details["status"] == "active"


@pytest.mark.parametrize("category", ["violao", "violão", "violoes", "violões", "Violões", "VIOLAO"])
def test_category_filter_tolerates_accents_and_number(tools, category):
    res = _run(tools["search_products"], category=category, max_price_brl=1000)
    names = [item["name"] for item in res]
    assert names, f"categoria {category!r} nao encontrou nada"
    assert all(item["category"] == "Violões" for item in res)
    assert any("Tagima Memphis" in n or "Yamaha C40" in n for n in names)


def test_category_filter_does_not_match_unrelated_category(tools):
    res = _run(tools["search_products"], category="violao", in_stock_only=False, limit=100)
    assert {item["category"] for item in res} == {"Violões"}


@pytest.mark.parametrize("category", ["sintetizador", "teclado sintetizador", "Synth"])
def test_unknown_category_text_falls_back_to_search_term(tools, category):
    res = _run(tools["search_products"], category=category, max_price_brl=2000)
    assert [item["name"] for item in res] == ["Teclado Sintetizador Korg Synth 1 Pro"]


def test_unknown_category_without_any_match_returns_empty(tools):
    assert _run(tools["search_products"], category="acessorios", in_stock_only=False) == []
