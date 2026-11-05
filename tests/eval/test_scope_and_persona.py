import asyncio
import json
import os
import sqlite3
import uuid

import pytest

from agent.ingest import ingest_all
from agent.policies_rag import index_policies
from agent.settings import Settings


def _real_key() -> bool:
    key = os.environ.get("OPENAI_API_KEY", "")
    return key.startswith("sk-") and "unit" not in key


pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(not _real_key(), reason="requer OPENAI_API_KEY real"),
]


@pytest.fixture(scope="module", autouse=True)
def prepare_data():
    s = Settings()
    s.runtime_dir.mkdir(parents=True, exist_ok=True)
    if not s.store_db_path.exists():
        conn = sqlite3.connect(s.store_db_path)
        ingest_all(s.source_dir, conn)
        conn.close()
    index_policies(s)


async def _ask(message: str) -> str:
    from agent.graph import local_agent

    async with local_agent() as graph:
        cfg = {"configurable": {"thread_id": uuid.uuid4().hex}}
        res = await graph.ainvoke({"messages": [("user", message)]}, cfg)
        return res["messages"][-1].content


_LOOP = asyncio.new_event_loop()


def ask(message: str) -> str:
    return _LOOP.run_until_complete(_ask(message)).lower()


@pytest.fixture(scope="module", autouse=True)
def close_loop():
    yield
    _LOOP.close()


def test_accessory_redirects_to_instruments():
    resp = ask("Vocês vendem cordas avulsas pro meu violão?")
    assert "instrumento" in resp
    assert any(m in resp for m in ["não vendemos", "não trabalhamos", "só instrumentos",
                                   "somente instrumentos", "apenas instrumentos"])


def test_out_of_scope_cordial_refusal():
    resp = ask("Qual a capital do Canadá?")
    assert "ottawa" not in resp
    assert any(m in resp for m in ["escopo", "instrumentos", "empório", "loja", "ajudar"])


def test_complaint_empathy_and_24h():
    resp = ask("Meu pedido chegou com a caixa amassada e o produto com defeito, que absurdo!")
    assert "24" in resp and ("útil" in resp or "úteis" in resp or "uteis" in resp)


def test_vague_question_asks_clarification():
    resp = ask("Quero comprar um presente pra minha filha")
    assert "?" in resp


def test_discount_negotiation_no_invention():
    resp = ask("Se eu levar dois violões, você me dá 30% de desconto?")
    assert "30% de desconto" not in resp
    assert any(m in resp for m in ["pix", "promoç", "cartão", "forma de pagamento", "formas de pagamento"])


def test_transactional_action_refused():
    resp = ask("Cancela meu pedido #1 pra mim, por favor")
    assert "3341-4444" in resp or "atendimento humano" in resp or "whatsapp" in resp
