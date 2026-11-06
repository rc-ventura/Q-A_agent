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
