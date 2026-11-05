import sqlite3
from pathlib import Path

import pytest

pytest.importorskip("chromadb")

from agent.ingest import ingest_all
from agent.policies_rag import (
    chunk_text,
    extract_pdf_sections,
    index_policies,
    search_policies,
    section_chunks,
)
from agent.settings import Settings
from agent.tools.store_info import get_store_info

PDF = Path("data/source/politicas_da_loja.pdf")


def test_chunk_text_bounds():
    chunks = chunk_text("paragrafo\n\n" * 200, chunk_chars=800, overlap=100)
    assert all(len(c) <= 1000 for c in chunks)
    assert len(chunks) > 1


def test_chunk_empty():
    assert chunk_text("") == []


@pytest.mark.skipif(not PDF.exists(), reason="pdf fonte ausente")
def test_extract_sections_structure():
    sections = extract_pdf_sections(PDF)
    assert len(sections) >= 15
    assert all(s["section_no"] and s["section_title"] and s["page"] >= 1 for s in sections)
    assert all(s["text"] for s in sections)
    nos = {s["section_no"] for s in sections}
    assert {"1", "2", "4.1"} <= nos
    horarios = next(s for s in sections if s["section_no"] == "2")
    assert "Horário" in horarios["section_title"]


def test_section_chunks_deterministic_ids():
    sec = {"section_no": "4.1", "section_title": "Arrependimento", "page": 5,
           "text": "x" * 3000}
    chunks = section_chunks(sec)
    assert len(chunks) >= 2
    assert chunks[0]["id"] == "policy_4_1_1"
    again = section_chunks(sec)
    assert [c["id"] for c in again] == [c["id"] for c in chunks]
    assert all(c["section_no"] == "4.1" and c["page"] == 5 for c in chunks)


@pytest.mark.skipif(not PDF.exists(), reason="pdf fonte ausente")
def test_index_idempotent_and_search_metadata(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    s = Settings()
    coll = index_policies(s, persist_dir=str(tmp_path))
    n1 = coll.count()
    assert n1 >= 10
    coll = index_policies(s, persist_dir=str(tmp_path))
    assert coll.count() == n1
    hits = search_policies(coll, "horário de funcionamento", s.rag_min_score, limit=3)
    assert isinstance(hits, list)
    for h in hits:
        assert "score" in h and "section_no" in h and "section_title" in h


def test_get_store_info_matches_manual():
    info = get_store_info()
    assert "14 de Maio, 3200" in info["endereco"]
    assert info["telefone_whatsapp"] == "(67) 3341-4444"
    assert info["horario"]["segunda_a_sexta"] == "09:00 às 18:00"
    assert info["horario"]["domingo_e_feriados"] == "Fechado"
    assert "@" in info["email"]


def test_active_promotions_view():
    conn = sqlite3.connect(":memory:")
    ingest_all(Settings().source_dir, conn)
    rows = conn.execute(
        "SELECT price_brl, discount_percent, final_price_brl FROM v_active_promotions"
    ).fetchall()
    assert rows, "manual espera promocoes ativas nos dados fonte"
    for price, disc, final in rows:
        assert final == round(price * (1 - disc / 100), 2)
