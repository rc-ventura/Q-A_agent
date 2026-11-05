import asyncio

import httpx
import openai
import pytest
from langchain_core.messages import AIMessageChunk, ToolMessage

from app.chat import TOOL_TITLES, friendly_error, stream_reply


class FakeGraph:
    def __init__(self, events, error=None):
        self.events = events
        self.error = error
        self.calls = []

    async def astream(self, payload, config, stream_mode):
        self.calls.append((payload, config, stream_mode))
        for event in self.events:
            yield event, {}
        if self.error:
            raise self.error


def text(token):
    return AIMessageChunk(content=token)


def tool_call(name):
    return AIMessageChunk(
        content="", tool_calls=[{"name": name, "args": {}, "id": "c1", "type": "tool_call"}]
    )


def collect(graph, message="oi", thread_id="t1"):
    async def run():
        return [snapshot async for snapshot in stream_reply(graph, message, thread_id)]

    return asyncio.run(run())


def request():
    return httpx.Request("POST", "https://api.openai.com/v1/chat/completions")


def test_streams_text_tokens_into_one_growing_message():
    snapshots = collect(FakeGraph([text("Olá"), text(", tudo"), text(" bem?")]))
    assert snapshots[0] == [{"role": "assistant", "content": "Olá"}]
    assert snapshots[-1] == [{"role": "assistant", "content": "Olá, tudo bem?"}]


def test_sends_message_with_thread_id_in_messages_mode():
    graph = FakeGraph([text("ok")])
    collect(graph, message="Qual o endereço?", thread_id="abc")
    payload, config, mode = graph.calls[0]
    assert payload == {"messages": [("user", "Qual o endereço?")]}
    assert config == {"configurable": {"thread_id": "abc"}}
    assert mode == "messages"


def test_tool_call_becomes_pending_block_then_done_after_result():
    events = [
        tool_call("specialist_catalog"),
        ToolMessage(content="dados", tool_call_id="c1"),
        text("R$ 2.199,00"),
    ]
    snapshots = collect(FakeGraph(events))
    assert snapshots[0][0]["metadata"] == {"title": "Consultando catálogo…", "status": "pending"}
    final = snapshots[-1]
    assert final[0]["metadata"] == {"title": "Consultando catálogo…", "status": "done"}
    assert final[1] == {"role": "assistant", "content": "R$ 2.199,00"}


def test_tool_message_content_is_not_shown_as_reply():
    events = [tool_call("specialist_policies"), ToolMessage(content="SEGREDO", tool_call_id="c1")]
    snapshots = collect(FakeGraph(events))
    assert all("SEGREDO" not in m["content"] for s in snapshots for m in s)


def test_empty_tool_name_chunks_are_ignored():
    events = [tool_call("specialist_orders"), tool_call(""), text("pronto")]
    final = (collect(FakeGraph(events)))[-1]
    assert [m.get("metadata", {}).get("title") for m in final] == [
        "Consultando pedidos…",
        None,
    ]


def test_each_specialist_has_its_own_title():
    assert TOOL_TITLES == {
        "specialist_catalog": "Consultando catálogo…",
        "specialist_policies": "Consultando políticas…",
        "specialist_orders": "Consultando pedidos…",
        "specialist_service": "Encaminhando ao atendimento…",
    }


def test_runtime_error_keeps_partial_reply_and_appends_friendly_message():
    graph = FakeGraph([text("Um instante")], error=RuntimeError("sk-vazou"))
    final = (collect(graph))[-1]
    assert final[0]["content"] == "Um instante"
    assert "tente novamente" in final[-1]["content"].lower()
    assert "sk-vazou" not in str(final)


def test_friendly_error_auth_points_to_key():
    exc = openai.AuthenticationError(
        "Incorrect API key sk-proj-abc", response=httpx.Response(401, request=request()), body=None
    )
    message = friendly_error(exc)
    assert "chave" in message.lower()
    assert "sk-proj-abc" not in message


def test_friendly_error_rate_limit():
    exc = openai.RateLimitError(
        "limite", response=httpx.Response(429, request=request()), body=None
    )
    assert "muitas" in friendly_error(exc).lower()


@pytest.mark.parametrize(
    "exc",
    [openai.APIConnectionError(request=request()), openai.APITimeoutError(request=request())],
)
def test_friendly_error_provider_unreachable(exc):
    assert "fora do ar" in friendly_error(exc).lower()


def test_friendly_error_generic_includes_human_contact():
    message = friendly_error(ValueError("qualquer coisa interna"))
    assert "(67) 3341-4444" in message
    assert "qualquer coisa interna" not in message
