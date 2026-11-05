import json

import pytest

from agent.policies_rag import index_policies
from agent.settings import Settings
from agent.tools.policies import make_policies_tools


@pytest.fixture(scope="module")
def coll(tmp_path_factory):
    return index_policies(Settings(), persist_dir=str(tmp_path_factory.mktemp("chroma")))


@pytest.fixture(scope="module")
def tools(coll):
    return {t.name: t for t in make_policies_tools(Settings(), collection=coll)}


def _run(tool, **kwargs):
    return json.loads(tool.invoke(kwargs))


def test_arrependimento_returns_section4_chunk(tools):
    res = _run(tools["search_policies"], question="posso devolver porque me arrependi")
    assert "chunks" in res and res["chunks"]
    text = " ".join(c["text"] for c in res["chunks"]).lower()
    assert "7 (sete) dias" in text
    assert "10 dias úteis" in text
    assert all("section_title" in c for c in res["chunks"])
    assert any(c["section_no"].startswith("4") for c in res["chunks"])


def test_chunks_respect_min_score(tools):
    res = _run(tools["search_policies"], question="formas de pagamento")
    assert all(c["similarity"] >= Settings().rag_min_score for c in res.get("chunks", []))


def test_weak_retrieval_marker(coll):
    tools_strict = {t.name: t for t in make_policies_tools(Settings(), collection=coll, min_score=0.99)}
    res = _run(tools_strict["search_policies"], question="política de entrega")
    assert res == {"retrieval": "weak"}


def test_raw_text_not_summarized(tools):
    res = _run(tools["search_policies"], question="horário de funcionamento")
    assert any("09:00" in c["text"] for c in res.get("chunks", []))


def test_get_store_info_fixed_block(tools):
    res = _run(tools["get_store_info"])
    assert "14 de Maio, 3200" in res["endereco"]
    assert res["telefone_whatsapp"] == "(67) 3341-4444"
    assert res["horario"]["segunda_a_sexta"] == "09:00 às 18:00"
    assert res["horario"]["sabado"] == "09:00 às 13:00"
