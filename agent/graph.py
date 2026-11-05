from langchain.agents import create_agent
from langchain_core.tools import tool
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent import specialists
from agent.prompt import DISPATCHER_SYSTEM_PROMPT
from agent.settings import Settings, get_settings

_SPECIALIST_SPECS = [
    ("catalog", "Perguntas sobre produtos, precos, estoque, promocoes e indicacoes de instrumentos.", specialists.catalog),
    ("policies", "Perguntas sobre trocas, devolucoes, garantia, pagamentos, entrega, horarios, endereco e LGPD.", specialists.policies),
    ("orders", "Consultas de status, rastreio e historico de pedidos do cliente.", specialists.orders),
    ("service", "Saudacoes, elogios, reclamacoes e assuntos fora do escopo da loja.", specialists.service),
]


def _wrap_specialist(name: str, description: str, agent):
    """Encapsula um especialista compilado como tool do dispatcher.

    O dispatcher chama a tool com a pergunta completa do cliente; a tool
    executa o especialista e devolve a resposta textual dele.
    """

    @tool
    async def _run(question: str) -> str:
        """Delega a pergunta do cliente ao especialista do dominio."""
        result = await agent.ainvoke({"messages": [("user", question)]})
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
        model=f"openai:{s.openai_model}",
        tools=specialist_tools(s),
        system_prompt=DISPATCHER_SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )


def build_local_agent(settings: Settings | None = None):
    """Dispatcher para execucao local com checkpoints SQLite (modo A)."""
    s = settings or get_settings()
    s.runtime_dir.mkdir(parents=True, exist_ok=True)
    return build_agent(
        checkpointer=AsyncSqliteSaver.from_conn_string(str(s.checkpoint_db_path)),
        settings=s,
    )


graph = build_agent()
