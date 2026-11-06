import uuid

import gradio as gr

from app.bootstrap import activate_key, check_api_key, ensure_data
from app.chat import stream_reply
from agent.settings import Settings, get_settings

TITLE = "# Empório da Música\nAtendimento ao cliente"


def new_thread_id() -> str:
    """Gera o identificador de uma nova conversa (o checkpoint anterior permanece no SQLite)."""
    return uuid.uuid4().hex


async def respond(message: str, history: list, thread_id: str):
    """Fluxo F1: atende uma mensagem com streaming e blocos de tool call.

    Args:
        message: texto do cliente.
        history: historico exibido pelo Gradio (o contexto real vem do checkpointer).
        thread_id: conversa da sessao atual.

    Yields:
        Mensagens do assistente conforme produzidas pelo grafo.
    """
    from agent.graph import local_agent

    async with local_agent() as graph:
        async for snapshot in stream_reply(graph, message, thread_id):
            yield snapshot


def build_ui(has_valid_key: bool, settings: Settings | None = None) -> gr.Blocks:
    """Monta a aplicacao: onboarding da chave (F0) e chat de atendimento (F1).

    Args:
        has_valid_key: True entra direto no chat; False mostra a tela de configuracao.
        settings: configuracao (padrao: ``get_settings()``).

    Returns:
        Blocos Gradio prontos para ``launch()``.
    """
    settings = settings or get_settings()

    with gr.Blocks(title="Empório da Música — Atendimento") as demo:
        gr.Markdown(TITLE)

        with gr.Column(visible=not has_valid_key) as onboarding:
            gr.Markdown(
                "### Configure a chave da OpenAI\n"
                "Cole a chave para ativar o atendimento. Ela fica salva apenas no `.env` local."
            )
            key_input = gr.Textbox(label="OPENAI_API_KEY", type="password")
            save_button = gr.Button("Salvar e começar", variant="primary")
            status = gr.Markdown("")

        with gr.Column(visible=has_valid_key) as chat_area:
            thread = gr.State(new_thread_id)
            chatbot = gr.Chatbot(height=520)
            chat = gr.ChatInterface(respond, additional_inputs=[thread], chatbot=chatbot)
            new_chat = gr.Button("Nova conversa")
            # chatbot_state e a copia interna do historico do ChatInterface: sem zera-la,
            # a conversa anterior reaparece na tela na proxima mensagem.
            new_chat.click(
                lambda: (new_thread_id(), [], []),
                outputs=[thread, chatbot, chat.chatbot_state],
            )
            chatbot.clear(new_thread_id, outputs=[thread])

        def submit_key(key: str):
            error = activate_key(key or "", settings=settings)
            if error:
                return error, gr.Textbox(), gr.Column(visible=True), gr.Column(visible=False)
            return "", gr.Textbox(value=""), gr.Column(visible=False), gr.Column(visible=True)

        save_button.click(
            submit_key,
            inputs=[key_input],
            outputs=[status, key_input, onboarding, chat_area],
        )

    return demo


def launch() -> None:
    """Sobe a UI na porta 7860, preparando os dados quando ja ha chave valida."""
    settings = get_settings()
    key = settings.openai_api_key
    has_valid_key = bool(key) and check_api_key(key.get_secret_value()) is None
    if has_valid_key:
        ensure_data(settings)
    build_ui(has_valid_key, settings).launch()
