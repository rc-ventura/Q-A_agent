import copy
import logging
from collections.abc import AsyncIterator

import openai
from langchain_core.messages import AIMessageChunk, ToolMessage

logger = logging.getLogger(__name__)

HUMAN_CONTACT = "WhatsApp (67) 3341-4444"

TOOL_TITLES = {
    "specialist_catalog": "Consultando catálogo…",
    "specialist_policies": "Consultando políticas…",
    "specialist_orders": "Consultando pedidos…",
    "specialist_service": "Encaminhando ao atendimento…",
}


def friendly_error(exc: Exception) -> str:
    """Traduz uma falha de runtime em mensagem amigavel em pt-BR para o cliente.

    Nunca inclui o texto da excecao: mensagens de provedores podem ecoar
    trechos da chave de API.

    Args:
        exc: excecao levantada durante o atendimento.

    Returns:
        Mensagem com a orientacao adequada ao tipo de falha (chave invalida,
        limite de requisicoes, provedor fora do ar ou erro generico).
    """
    if isinstance(exc, openai.AuthenticationError):
        return (
            "Não consegui acessar o serviço de IA: a chave da OpenAI parece inválida ou "
            "expirada. Verifique a chave e tente novamente."
        )
    if isinstance(exc, openai.RateLimitError):
        return "Estamos com muitas solicitações no momento. Aguarde alguns instantes e tente novamente."
    if isinstance(exc, (openai.APIConnectionError, openai.InternalServerError)):
        return (
            "Nosso atendimento está fora do ar no momento. Tente novamente em instantes "
            f"ou fale com a gente pelo {HUMAN_CONTACT}."
        )
    return (
        "Tive um problema ao processar sua mensagem. Tente novamente ou fale com nossa "
        f"equipe pelo {HUMAN_CONTACT}."
    )


def _is_tool_block(message: dict) -> bool:
    return "metadata" in message


def _append_text(messages: list[dict], token: str) -> None:
    if messages and not _is_tool_block(messages[-1]):
        messages[-1]["content"] += token
    else:
        messages.append({"role": "assistant", "content": token})


def _finish_tool_blocks(messages: list[dict]) -> None:
    for message in messages:
        if _is_tool_block(message):
            message["metadata"]["status"] = "done"


async def stream_reply(graph, message: str, thread_id: str) -> AsyncIterator[list[dict]]:
    """Executa um turno no grafo e emite o estado atual da resposta a cada evento.

    Cada chamada de tool do dispatcher vira um bloco recolhivel (titulo pt-BR,
    status pending ate o resultado chegar); os tokens do modelo crescem em uma
    mensagem de texto separada. Resultados brutos de tools nao sao exibidos.

    Args:
        graph: grafo compilado com checkpointer (expoe ``astream``).
        message: texto do cliente.
        thread_id: identificador da conversa no checkpointer.

    Yields:
        Lista completa de mensagens do assistente (formato ``messages`` do
        Gradio) refletindo tudo o que foi produzido ate o momento. Em caso de
        falha, a lista termina com a mensagem amigavel de ``friendly_error``.
    """
    messages: list[dict] = []
    try:
        async for chunk, _metadata in graph.astream(
            {"messages": [("user", message)]},
            {"configurable": {"thread_id": thread_id}},
            stream_mode="messages",
        ):
            changed = False
            if isinstance(chunk, ToolMessage):
                _finish_tool_blocks(messages)
                changed = True
            elif isinstance(chunk, AIMessageChunk):
                for call in chunk.tool_calls:
                    if call["name"]:
                        title = TOOL_TITLES.get(call["name"], "Consultando…")
                        messages.append(
                            {
                                "role": "assistant",
                                "content": "",
                                "metadata": {"title": title, "status": "pending"},
                            }
                        )
                        changed = True
                if chunk.content:
                    _append_text(messages, chunk.content)
                    changed = True
            if changed:
                yield copy.deepcopy(messages)
    except Exception as exc:
        logger.error("falha no atendimento: %s", type(exc).__name__)
        _finish_tool_blocks(messages)
        messages.append({"role": "assistant", "content": friendly_error(exc)})
        yield copy.deepcopy(messages)
