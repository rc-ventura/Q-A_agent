from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from pypdf import PdfReader


def extract_pdf_text(pdf_path: Path) -> str:
    """Extrai o texto integral do PDF de politicas, pagina por pagina."""
    reader = PdfReader(str(pdf_path))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def chunk_text(text: str, chunk_chars: int = 800, overlap: int = 100) -> list[str]:
    """Divide o texto em janelas sobrepostas, preferindo cortes em paragrafo.

    Garante que nenhum chunk exceda chunk_chars + overlap caracteres.
    """
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_chars, len(text))
        if end < len(text):
            cut = text.rfind("\n\n", start, end + overlap)
            if cut > start:
                end = cut
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _embedder():
    """Embeddings OpenAI (funcao nomeada p/ injecao em testes)."""
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(model="text-embedding-3-small")


def build_collection(text: str, persist_dir: str) -> "chromadb.api.Collection":
    """Indexa os chunks do manual num collection Chroma persistente."""
    chunks = chunk_text(text)
    client = chromadb.PersistentClient(
        path=persist_dir, settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True)
    )
    coll = client.get_or_create_collection("policies")
    if coll.count() == 0:
        import uuid

        coll.add(
            ids=[str(uuid.uuid4()) for _ in chunks],
            documents=chunks,
        )
    return coll


def index_policies(settings, persist_dir: str | None = None):
    """Pipeline completo: extrai PDF, indexa em Chroma e devolve o collection."""
    text = extract_pdf_text(settings.source_dir / "politicas_da_loja.pdf")
    return build_collection(text, persist_dir or str(settings.chroma_dir))


def search_policies(coll, query: str, min_score: float, limit: int = 3) -> list[dict]:
    """Busca os chunks mais proximos da query (score >= min_score)."""
    res = coll.query(query_texts=[query], n_results=limit)
    return [
        {"text": doc, "score": 1.0 - dist}
        for doc, dist in zip(res["documents"][0], res["distances"][0])
        if (1.0 - dist) >= min_score
    ]
