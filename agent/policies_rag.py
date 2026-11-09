import re
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.errors import NotFoundError
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from pypdf import PdfReader

SECTION_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2})?)(?:\. | )(\S.*)$")
NOISE_RE = re.compile(r"^\s*(Página \d+|Empório da Música Manual de Políticas.*)$")
COLLECTION_NAME = "policies"
STAGING_NAME = "policies_staging"
EMBEDDING_MODEL = "text-embedding-3-small"
MAX_CHUNK_CHARS = 1200
OVERLAP = 150


def chunk_text(text: str, chunk_chars: int = MAX_CHUNK_CHARS, overlap: int = OVERLAP) -> list[str]:
    """Divide texto em janelas sobrepostas, preferindo cortes em paragrafo.

    Garante que nenhum chunk exceda chunk_chars + overlap caracteres. O corte em
    paragrafo so e usado quando deixa um chunk maior que o overlap; senao a janela
    avancaria quase nada por vez e geraria chunks minusculos e redundantes.
    """
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_chars, len(text))
        if end < len(text):
            cut = text.rfind("\n\n", start, end + overlap)
            if cut > start + overlap:
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


def _client(persist_dir: str):
    """Cliente Chroma persistente; todos os acessos usam as mesmas opcoes (exigencia do Chroma por diretorio)."""
    return chromadb.PersistentClient(
        path=persist_dir, settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True)
    )


def openai_embedding_function() -> OpenAIEmbeddingFunction:
    """Embeddings OpenAI para o indice de politicas.

    A chave e lida da variavel OPENAI_API_KEY no momento do uso (o Chroma
    persiste apenas o NOME da variavel, nunca o segredo). Medido no manual da
    loja: a secao correta fica no top-3 em 12/12 perguntas, contra 8/12 do
    MiniLM padrao do Chroma, que e um modelo em ingles (ver LL-0002).
    """
    return OpenAIEmbeddingFunction(model_name=EMBEDDING_MODEL, api_key_env_var="OPENAI_API_KEY")


def build_collection(sections: list[dict], persist_dir: str, embedding_function) -> "chromadb.api.Collection":
    """Reconstroi o indice de politicas no Chroma persistente (espaco cosseno).

    O indice e derivado do PDF, entao e recriado do zero a cada chamada: isso
    mantem a operacao idempotente (IDs deterministicos, sem duplicar) e evita
    conflito quando muda a funcao de embedding ou o espaco de distancia de um
    indice gravado por versao anterior.

    Args:
        sections: secoes extraidas do manual.
        persist_dir: diretorio do Chroma persistente.
        embedding_function: funcao de embedding usada na indexacao e nas consultas.

    Returns:
        A collection ``policies`` populada.
    """
    client = _client(persist_dir)
    # Constroi numa colecao temporaria e so troca pela definitiva depois que os
    # embeddings deram certo: uma falha (sem rede, 401, limite) nao pode deixar o
    # indice vazio nem apagar o indice anterior.
    try:
        client.delete_collection(STAGING_NAME)
    except NotFoundError:
        pass
    staging = client.create_collection(
        STAGING_NAME,
        embedding_function=embedding_function,
        configuration={"hnsw": {"space": "cosine"}},
    )
    try:
        chunks = [c for s in sections for c in section_chunks(s)]
        if chunks:
            staging.upsert(
                ids=[c["id"] for c in chunks],
                documents=[
                    f"Secao {c['section_no']} — {c['section_title']}\n\n{c['text']}"
                    for c in chunks
                ],
                metadatas=[
                    {k: c[k] for k in ("section_no", "section_title", "page")} for c in chunks
                ],
            )
    except BaseException:
        client.delete_collection(STAGING_NAME)
        raise
    try:
        client.delete_collection(COLLECTION_NAME)
    except NotFoundError:
        pass
    staging.modify(name=COLLECTION_NAME)
    return staging


def index_policies(settings, persist_dir: str | None = None, embedding_function=None):
    """Pipeline completo: PDF -> secoes -> chunks -> Chroma.

    Args:
        settings: configuracao com ``source_dir`` e ``chroma_dir``.
        persist_dir: sobrescreve ``settings.chroma_dir`` (testes).
        embedding_function: padrao ``openai_embedding_function()``; testes
            injetam a funcao local para rodar sem rede.
    """
    sections = extract_pdf_sections(settings.source_dir / "politicas_da_loja.pdf")
    return build_collection(
        sections,
        persist_dir or str(settings.chroma_dir),
        embedding_function or openai_embedding_function(),
    )


def open_policies(settings, persist_dir: str | None = None, embedding_function=None):
    """Abre o indice de politicas ja existente; so indexa se ele ainda nao existir.

    E o caminho de consulta (tools): nao reconstroi o indice, o que seria
    destrutivo para consultas concorrentes. A reconstrucao fica a cargo de
    ``index_policies``, chamada uma vez na inicializacao.

    Args:
        settings: configuracao com ``source_dir`` e ``chroma_dir``.
        persist_dir: sobrescreve ``settings.chroma_dir`` (testes).
        embedding_function: padrao ``openai_embedding_function()``.

    Returns:
        A collection ``policies`` pronta para consulta.
    """
    directory = persist_dir or str(settings.chroma_dir)
    embedding_function = embedding_function or openai_embedding_function()
    try:
        coll = _client(directory).get_collection(COLLECTION_NAME, embedding_function=embedding_function)
    except NotFoundError:
        coll = None
    if coll is None or coll.count() == 0:
        # Indice ausente ou vazio (ex.: partida anterior interrompida): reconstroi.
        return index_policies(settings, persist_dir=directory, embedding_function=embedding_function)
    return coll


def search_policies(coll, query: str, min_score: float, limit: int = 3) -> list[dict]:
    """Top-k chunks por similaridade cosseno; descarta scores < min_score.

    O indice usa espaco cosseno, entao ``score = 1 - distancia``. Sem trecho
    forte o especialista deve recusar em vez de improvisar regra (FP1).
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
