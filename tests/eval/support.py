import asyncio
import os
import time
import uuid
from dataclasses import dataclass

import pytest

MAX_SECONDS = 30


def has_real_key() -> bool:
    key = os.environ.get("OPENAI_API_KEY", "")
    return key.startswith("sk-") and "unit" not in key


requires_real_key = pytest.mark.skipif(not has_real_key(), reason="requer OPENAI_API_KEY real")


@dataclass(frozen=True)
class Reply:
    text: str
    seconds: float


class Agent:
    """Cliente sincrono do agente real, com uma conversa (thread) por chamada ou reutilizada."""

    def __init__(self):
        self._loop = asyncio.new_event_loop()

    def ask(self, message: str, thread_id: str | None = None) -> Reply:
        """Envia uma mensagem e devolve a resposta em minusculas com a latencia medida."""
        started = time.perf_counter()
        text = self._loop.run_until_complete(self._ask(message, thread_id or uuid.uuid4().hex))
        return Reply(text.lower(), time.perf_counter() - started)

    async def _ask(self, message: str, thread_id: str) -> str:
        from agent.graph import local_agent

        async with local_agent() as graph:
            result = await graph.ainvoke(
                {"messages": [("user", message)]}, {"configurable": {"thread_id": thread_id}}
            )
        return result["messages"][-1].content

    def close(self) -> None:
        self._loop.close()


def price(value: float) -> tuple[str, ...]:
    """Grafias aceitas de um valor em reais (ex.: 2199.0 -> '2.199,00', '2.199', '2199')."""
    br = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    variants = [br, br.replace(".", ""), f"{value:.2f}"]
    if br.endswith(",00"):
        variants += [br[:-3], br[:-3].replace(".", "")]
    return tuple(dict.fromkeys(variants))


def assert_reply(reply: Reply, required=(), forbidden=()) -> None:
    """Valida fatos-chave (cada item de ``required`` e um grupo de alternativas) e a latencia."""
    for alternatives in required:
        options = (alternatives,) if isinstance(alternatives, str) else alternatives
        assert any(o in reply.text for o in options), f"faltou {options} em: {reply.text}"
    for term in forbidden:
        assert term not in reply.text, f"nao deveria conter {term!r}: {reply.text}"
    assert reply.seconds <= MAX_SECONDS, f"resposta em {reply.seconds:.1f}s (limite {MAX_SECONDS}s)"
