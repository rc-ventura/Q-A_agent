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
