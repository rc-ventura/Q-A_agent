import pytest

pytest.importorskip("chromadb")

from agent.policies_rag import chunk_text, extract_pdf_text, build_collection


def test_chunk_text_bounds():
    chunks = chunk_text("paragrafo\n\n" * 200, chunk_chars=800, overlap=100)
    assert all(len(c) <= 1000 for c in chunks)
    assert len(chunks) > 1


def test_chunk_empty():
    assert chunk_text("") == []


def test_extract_and_index(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    pdf = __import__("pathlib").Path("data/source/politicas_da_loja.pdf")
    if not pdf.exists():
        pytest.skip("pdf fonte ausente")
    text = extract_pdf_text(pdf)
    assert "troca" in text.lower() or "pol" in text.lower()
    coll = build_collection(text, persist_dir=str(tmp_path))
    assert coll.count() >= 3


def test_query_returns_chunks(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste")
    from agent.settings import Settings
    from agent.policies_rag import index_policies, search_policies
    s = Settings()
    text = extract_pdf_text(s.source_dir / "politicas_da_loja.pdf")
    coll = index_policies(s, persist_dir=str(tmp_path))
    hits = search_policies(coll, "qual o horario de funcionamento", s.rag_min_score, limit=3)
    assert isinstance(hits, list)
