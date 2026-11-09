from langchain.agents import create_agent

from agent.contact import HUMAN_PHONE
from agent.llm import build_model
from agent.settings import Settings
from agent.tools.orders import make_orders_tools

SYSTEM_PROMPT = f"""Especialista em pedidos da Emporio da Musica.
Responda em portugues do Brasil, curto e cordial.
Para localizar um pedido, identifique o cliente primeiro pelo nome completo ou e-mail (nunca peca telefone nem outros dados) e depois liste os pedidos via tools.
Nunca invente status, rastreio, datas ou quantidades: use apenas o que os tools retornarem; a quantidade de cada item e o campo quantity.
Nao execute acoes transacionais: encaminhe ao humano {HUMAN_PHONE}.
Nunca exponha pedidos sem identificar o cliente; se houver varios candidatos, peca esclarecimento oferecendo nomes/cidades — nunca chute. Se nao houver nenhum candidato, diga que nao localizou o cadastro e peca o e-mail da compra; nao peca cidade nem outros dados.
Se find_customer devolver name_too_short ou truncated, peca o nome completo ou o e-mail; nunca liste todos os candidatos.
Ao relatar cancelamento, explique o motivo das notes com transparencia."""


def build(settings: Settings, db_path: str | None = None):
    """Especialista de pedidos (US3) com tools de cliente/pedidos (T033)."""
    return create_agent(
        model=build_model(settings),
        tools=make_orders_tools(db_path or str(settings.store_db_path)),
        system_prompt=SYSTEM_PROMPT,
    )
