import re
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from pypdf import PdfReader

SECTION_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2})?)(?:\. | )(\S.*)$")
NOISE_RE = re.compile(r"^\s*(Página \d+|Empório da Música Manual de Políticas.*)$")
MAX_CHUNK_CHARS = 1200
OVERLAP = 150


def chunk_text(text: str, chunk_chars: int = MAX_CHUNK_CHARS, overlap: int = OVERLAP) -> list[str]:
    """Divide texto em janelas sobrepostas, preferindo cortes em paragrafo.

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


def extract_pdf_sections(pdf_path: Path) -> list[dict]:
    """Extrai o manual em secoes numeradas com pagina de inicio.

    Extrai em modo layout (o modo padrao quebra palavra por linha). Titulos
    reais tem separador ponto+espaco simples ou espaco simples ("2. Horario",
    "7.2 Fluxo"); itens de lista interna usam ponto+espacos multiplos e sao
    rejeitados. Rodapes/cabecalhos de pagina sao descartados como ruido.
    """
    reader = PdfReader(str(pdf_path))
    sections: list[dict] = []
    current: dict | None = None
    for page_no, page in enumerate(reader.pages, start=1):
        for raw in (page.extract_text(extraction_mode="layout") or "").splitlines():
            match = SECTION_RE.match(raw.strip())
            if match and len(match.group(2)) <= 80:
                current = {
                    "section_no": match.group(1),
                    "section_title": match.group(2).strip(),
                    "page": page_no,
                    "lines": [],
                }
                sections.append(current)
            elif current is not None and not NOISE_RE.match(raw):
                current["lines"].append(raw)
    return [
        {k: s[k] for k in ("section_no", "section_title", "page")}
        | {"text": text}
        for s in sections
        if (text := "\n".join(s["lines"]).strip())
    ]


def section_chunks(section: dict) -> list[dict]:
    """Divide uma secao em chunks com IDs deterministicos e metadados.

    ID: ``policy_<secao com _>_<parte>`` — reingestao e idempotente (upsert).
    """
    parts = chunk_text(section["text"])
    return [
        {
            "id": f"policy_{section['section_no'].replace('.', '_')}_{i + 1}",
            "text": part,
            "section_no": section["section_no"],
            "section_title": section["section_title"],
            "page": section["page"],
        }
        for i, part in enumerate(parts)
    ]


def build_collection(sections: list[dict], persist_dir: str) -> "chromadb.api.Collection":
    """Indexa os chunks por secao no Chroma persistente (upsert idempotente)."""
    client = chromadb.PersistentClient(
        path=persist_dir, settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True)
    )
    coll = client.get_or_create_collection("policies")
    chunks = [c for s in sections for c in section_chunks(s)]
    if chunks:
        coll.upsert(
            ids=[c["id"] for c in chunks],
            documents=[c["text"] for c in chunks],
            metadatas=[
                {k: c[k] for k in ("section_no", "section_title", "page")} for c in chunks
            ],
        )
    return coll


def index_policies(settings, persist_dir: str | None = None):
    """Pipeline completo: PDF -> secoes -> chunks -> Chroma (idempotente)."""
    sections = extract_pdf_sections(settings.source_dir / "politicas_da_loja.pdf")
    return build_collection(sections, persist_dir or str(settings.chroma_dir))


def search_policies(coll, query: str, min_score: float, limit: int = 3) -> list[dict]:
    """Top-k chunks por similaridade; descarta scores abaixo de min_score.

    Cada hit traz o texto e os metadados da secao (FP1: sem trecho forte o
    especialista deve recusar em vez de improvisar regra).
    """
    res = coll.query(query_texts=[query], n_results=limit)
    hits = []
    for doc, dist, meta in zip(
        res["documents"][0], res["distances"][0], res["metadatas"][0]
    ):
        score = 1.0 - dist
        if score >= min_score:
            hits.append({"text": doc, "score": round(score, 3), **meta})
    return hits
