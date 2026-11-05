from langchain.agents import create_agent

from agent.settings import Settings
from agent.tools.orders import make_orders_tools

SYSTEM_PROMPT = """Especialista em pedidos da Emporio da Musica.
Responda em portugues do Brasil, curto e cordial.
Para localizar um pedido, identifique o cliente primeiro (nome/telefone) e depois liste os pedidos via tools.
Nunca invente status, rastreio ou datas: apenas o que os tools retornarem.
Nao execute acoes transacionais: encaminhe ao humano (67) 3341-4444.
Nunca exponha pedidos sem identificar o cliente; se houver varios candidatos, peca esclarecimento oferecendo nomes/cidades — nunca chute.
Ao relatar cancelamento, explique o motivo das notes com transparencia."""


def build(settings: Settings, db_path: str | None = None):
    """Especialista de pedidos (US3) com tools de cliente/pedidos (T033)."""
    return create_agent(
        model=f"openai:{settings.openai_model}",
        tools=make_orders_tools(db_path or str(settings.store_db_path)),
        system_prompt=SYSTEM_PROMPT,
    )
