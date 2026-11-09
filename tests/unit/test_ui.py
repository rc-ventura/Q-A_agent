import gradio as gr

from app.ui import build_ui


def test_build_ui_without_key_shows_onboarding_with_password_field():
    demo = build_ui(has_valid_key=False)
    assert isinstance(demo, gr.Blocks)
    passwords = [
        c for c in demo.blocks.values() if isinstance(c, gr.Textbox) and c.type == "password"
    ]
    assert len(passwords) == 1


def test_build_ui_with_key_builds_chat():
    demo = build_ui(has_valid_key=True)
    assert any(isinstance(c, gr.Chatbot) for c in demo.blocks.values())


def test_new_conversation_also_resets_chat_interface_history():
    """O ChatInterface guarda o historico num State proprio; limpar so o Chatbot o faz reaparecer."""
    demo = build_ui(has_valid_key=True)
    submit = next(d for d in demo.fns.values() if getattr(d.fn, "__name__", "") == "_submit_fn")
    history_state = submit.inputs[1]._id  # (mensagem, historico, *additional_inputs)
    button = next(
        b for b in demo.blocks.values() if isinstance(b, gr.Button) and b.value == "Nova conversa"
    )
    deps = [d for d in demo.fns.values() if any(t[0] == button._id for t in d.targets)]
    outputs = {o._id for d in deps for o in d.outputs}
    assert history_state in outputs
    assert any(isinstance(demo.blocks[i], gr.Chatbot) for i in outputs)


def test_respond_streams_from_local_agent(monkeypatch):
    """Caminho real do chat: respond abre o grafo local e repassa os snapshots do stream."""
    import asyncio
    from contextlib import asynccontextmanager

    from langchain_core.messages import AIMessageChunk

    import agent.graph as graph_module
    from app.ui import respond

    class FakeGraph:
        async def astream(self, payload, config, stream_mode):
            assert config["configurable"]["thread_id"] == "t-ui"
            assert payload["messages"][-1][1] == "oi"
            yield AIMessageChunk(content="Olá!"), {}

    @asynccontextmanager
    async def fake_local_agent():
        yield FakeGraph()

    monkeypatch.setattr(graph_module, "local_agent", fake_local_agent)

    async def run():
        return [s async for s in respond("oi", [], "t-ui")]

    snapshots = asyncio.run(run())
    assert snapshots[-1] == [{"role": "assistant", "content": "Olá!"}]


def test_submit_key_success_swaps_onboarding_for_chat(monkeypatch):
    import app.ui as ui

    monkeypatch.setattr(ui, "activate_key", lambda key, settings: None)
    status, box, onboarding, chat = ui.handle_key_submission("sk-ok", settings=object())
    assert status == ""
    assert onboarding.visible is False and chat.visible is True


def test_submit_key_rejection_keeps_onboarding_and_shows_message(monkeypatch):
    import app.ui as ui

    monkeypatch.setattr(ui, "activate_key", lambda key, settings: "Chave inválida")
    status, box, onboarding, chat = ui.handle_key_submission("sk-ruim", settings=object())
    assert status == "Chave inválida"
    assert onboarding.visible is True and chat.visible is False


def test_prepare_for_launch_survives_data_failure(monkeypatch):
    """Falha de embeddings na partida nao pode derrubar o app com traceback."""
    import app.ui as ui

    def boom(settings):
        raise RuntimeError("sem rede")

    monkeypatch.setattr(ui, "ensure_data", boom)
    assert ui.prepare_for_launch(object()) is False


def test_launch_enters_chat_when_key_unverified_by_network(monkeypatch):
    import app.ui as ui

    monkeypatch.setenv("OPENAI_API_KEY", "sk-guardada-no-env")
    monkeypatch.setattr(ui, "check_api_key", lambda key: "Não foi possível validar a chave agora")
    monkeypatch.setattr(ui, "ensure_data", lambda s: None)
    seen = {}

    class FakeDemo:
        def launch(self):
            seen["launched"] = True

    def fake_build(has_key, settings=None):
        seen["has_key"] = has_key
        return FakeDemo()

    monkeypatch.setattr(ui, "build_ui", fake_build)
    ui.launch()
    assert seen["has_key"] is True and seen["launched"] is True


def test_respond_setup_failure_becomes_friendly_message(monkeypatch):
    """Falha ao montar o agente (chave ausente, banco sem permissao) nao pode virar erro cru do Gradio."""
    import asyncio
    from contextlib import asynccontextmanager

    import agent.graph as graph_module
    from app.ui import respond

    @asynccontextmanager
    async def broken_local_agent():
        raise PermissionError("/data/runtime/checkpoints.db sk-vazou")
        yield

    monkeypatch.setattr(graph_module, "local_agent", broken_local_agent)

    async def run():
        return [s async for s in respond("oi", [], "t-ui")]

    snapshots = asyncio.run(run())
    final = snapshots[-1]
    assert "(67) 3341-4444" in final[-1]["content"]
    assert "sk-vazou" not in str(final)
