import json
import threading

from langchain_core.tools import tool

from agent.policies_rag import open_policies, search_policies as _rag_search
from agent.settings import Settings
from agent.tools.store_info import get_store_info as _store_info

_collection_cache: dict[str, object] = {}
_collection_lock = threading.Lock()


def _collection(settings: Settings):
    key = str(settings.chroma_dir)
    with _collection_lock:
        if key not in _collection_cache:
            _collection_cache[key] = open_policies(settings)
        return _collection_cache[key]


def make_policies_tools(settings: Settings, collection=None, min_score: float | None = None) -> list:
    """Tools de politicas fechados sobre a collection Chroma do manual.

    ``collection=None`` resolve a collection de settings.chroma_dir de forma
    lazy na primeira chamada (o index e criado no startup do app — T040 —
    para nao penalizar o primeiro cliente; aqui ele so e aberto); ``min_score`` sobrescreve
    settings.rag_min_score quando passado.
    """
    score = settings.rag_min_score if min_score is None else min_score

    @tool
    def search_policies(question: str, top_k: int = 3) -> str:
        """Consulta o manual de políticas da loja (RAG).

        Use para trocas, devoluções, arrependimento, garantia, pagamentos,
        parcelamento, entrega/frete, promoções/regras comerciais, atendimento
        e LGPD. Retorna JSON: {"chunks": [{section_no, section_title, page,
        text, similarity}]} com o trecho bruto do manual — baseie a resposta
        SOMENTE nesses trechos. Se vier {"retrieval": "weak"}, a informação
        não consta no manual: declare o limite e ofereça o canal humano.
        """
        hits = _rag_search(
            collection or _collection(settings),
            question,
            score,
            limit=top_k,
        )
        if not hits:
            return json.dumps({"retrieval": "weak"})
        return json.dumps(
            {
                "chunks": [
                    {
                        "section_no": h["section_no"],
                        "section_title": h["section_title"],
                        "page": h["page"],
                        "text": h["text"],
                        "similarity": h["score"],
                    }
                    for h in hits
                ]
            },
            ensure_ascii=False,
        )

    @tool
    def get_store_info() -> str:
        """Dados institucionais fixos: endereço, horários, telefone/WhatsApp.

        Use para "onde fica", "que horas abre", "qual o contato". Dados
        imutáveis do manual — sem busca semântica.
        """
        return json.dumps(_store_info(), ensure_ascii=False)

    return [search_policies, get_store_info]
