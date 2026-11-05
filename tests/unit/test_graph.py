import asyncio

from agent.graph import build_agent, specialist_tools
from agent.prompt import DISPATCHER_SYSTEM_PROMPT
from agent.settings import Settings


def _settings(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-unit-test-sem-rede")
    return Settings()


def test_dispatcher_exposes_only_specialist_tools(monkeypatch):
    tools = specialist_tools(_settings(monkeypatch))
    names = {t.name for t in tools}
    assert names == {
        "specialist_catalog",
        "specialist_policies",
        "specialist_orders",
        "specialist_service",
    }
    forbidden = {"write_file", "edit_file", "read_file", "execute", "ls", "glob", "grep"}
    assert not names & forbidden


def test_tool_descriptions_are_declarative(monkeypatch):
    for t in specialist_tools(_settings(monkeypatch)):
        assert t.description and "Passe a pergunta" in t.description


def test_prompt_has_persona_and_hard_rules():
    assert "Emporio da Musica" in DISPATCHER_SYSTEM_PROMPT
    for rule in ["Nunca invente", "transacionais", "LGPD", "(67) 3341-4444"]:
        assert rule in DISPATCHER_SYSTEM_PROMPT


def test_build_agent_compiles_without_checkpointer(monkeypatch):
    graph = build_agent(settings=_settings(monkeypatch))
    assert graph is not None


def test_local_agent_wires_async_sqlite_saver(monkeypatch):
    import asyncio

    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    from agent.graph import local_agent
    from agent.settings import Settings

    monkeypatch.setenv("OPENAI_API_KEY", "sk-unit-test-sem-rede")

    async def run():
        async with local_agent() as graph:
            assert isinstance(graph.checkpointer, AsyncSqliteSaver)
            cfg = {"configurable": {"thread_id": "unit-wiring-thread"}}
            assert await graph.checkpointer.aget_tuple(cfg) is None

    asyncio.run(run())
    assert Settings().checkpoint_db_path.exists()


def test_route_descriptions_send_store_questions_to_policies_not_service(monkeypatch):
    tools = {t.name: t.description.lower() for t in specialist_tools(_settings(monkeypatch))}
    for term in ["horario", "endereco", "frete", "parcelamento", "trocas", "boquilha"]:
        assert term in tools["specialist_policies"], term
    assert "nao use" in tools["specialist_service"]
    assert "politicas" in tools["specialist_service"]


def test_dispatcher_prefers_policies_when_in_doubt():
    prompt = DISPATCHER_SYSTEM_PROMPT.lower()
    assert "na duvida" in prompt and "prefira politicas" in prompt
    assert "use o especialista atendimento" not in prompt
