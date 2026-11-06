import logging
from contextlib import asynccontextmanager

from langchain.agents import create_agent
from langchain_core.tools import tool
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent import specialists
from agent.prompt import DISPATCHER_SYSTEM_PROMPT
from agent.llm import build_model
from agent.settings import Settings, get_settings

logger = logging.getLogger(__name__)

SPECIALIST_FAILURE_MESSAGE = (
    "Não consegui consultar essa informação agora. Peça ao cliente para tentar de novo "
    "ou indique o atendimento humano pelo WhatsApp (67) 3341-4444."
)

_SPECIALIST_SPECS = [
    ("catalog", "Perguntas sobre produtos, precos, estoque, promocoes, produtos descontinuados e indicacoes de instrumentos.", specialists.catalog),
    (
        "policies",
        "Informacoes institucionais e regras da loja: horario de funcionamento, endereco, telefone e "
        "contato, formas de pagamento, parcelamento, frete, prazos e valores de entrega, trocas e "
        "devolucoes de qualquer item (inclusive boquilha ou peca de instrumento), garantia e LGPD.",
        specialists.policies,
    ),
    ("orders", "Consultas de status, rastreio e historico de pedidos do cliente.", specialists.orders),
    (
        "service",
        "Somente saudacoes, elogios, reclamacoes (relato de problema sem perguntar regra), pedidos de acessorios (cordas, palhetas, cabos), "
        "negociacao de desconto, perguntas vagas, pedidos de acao (cancelar, alterar) e assuntos fora "
        "do escopo da loja. Nao use para duvidas sobre a loja ou suas politicas: essas vao para politicas.",
        specialists.service,
    ),
]


def _wrap_specialist(name: str, description: str, agent):
    """Encapsula um especialista compilado como tool do dispatcher.

    O dispatcher chama a tool com a pergunta completa do cliente; a tool
    executa o especialista e devolve a resposta textual dele. Uma falha do
    especialista (rate limit, timeout, erro de embedding) vira resultado da
    tool em vez de excecao: se a excecao escapasse, o checkpoint ficaria com
    ``tool_calls`` sem ``ToolMessage`` e a conversa nao poderia continuar.
    """

    @tool
    async def _run(question: str) -> str:
        """Delega a pergunta do cliente ao especialista do dominio."""
        try:
            result = await agent.ainvoke({"messages": [("user", question)]})
        except Exception as exc:
            logger.error("especialista %s falhou: %s", name, type(exc).__name__)
            return SPECIALIST_FAILURE_MESSAGE
        return result["messages"][-1].content

    _run.name = f"specialist_{name}"
    _run.description = f"{description} Passe a pergunta completa do cliente."
    return _run


def specialist_tools(settings: Settings):
    """Tools-roteadoras do dispatcher (uma por dominio/user story)."""
    return [
        _wrap_specialist(name, desc, builder(settings))
        for name, desc, builder in _SPECIALIST_SPECS
    ]


def build_agent(checkpointer=None, settings: Settings | None = None):
    """Compila o grafo dispatcher (ADR-0004).

    Sem checkpointer: variante para o Agent Server do blueprint (o server
    injeta o dele). Com checkpointer (ex.: AsyncSqliteSaver): modo local
    single-process.
    """
    s = settings or get_settings()
    return create_agent(
        model=build_model(s),
        tools=specialist_tools(s),
        system_prompt=DISPATCHER_SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )


@asynccontextmanager
async def local_agent(settings: Settings | None = None):
    """Dispatcher para execucao local com checkpoints SQLite (modo A).

    ``AsyncSqliteSaver.from_conn_string`` devolve um context manager cujo
    saver real so existe dentro do bloco — por isso a factory e um async
    context manager que entra no saver, compila o grafo com ele ativo e
    devolve o grafo pronto para uso com ``thread_id``.
    """
    s = settings or get_settings()
    s.runtime_dir.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(s.checkpoint_db_path)) as saver:
        yield build_agent(checkpointer=saver, settings=s)


graph = build_agent()
