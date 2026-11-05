from langchain.agents import create_agent

from agent.settings import Settings

SYSTEM_PROMPT = """Especialista em pedidos da Emporio da Musica.
Responda em portugues do Brasil, curto e cordial.
Para localizar um pedido, identifique o cliente primeiro (nome/telefone) e depois liste os pedidos via tools.
Nunca invente status, rastreio ou datas: apenas o que os tools retornarem.
Nao execute acoes transacionais: encaminhe ao humano (67) 3341-4444."""


def build(settings: Settings):
    """Especialista de pedidos (US3): tools find_customer/list_orders entram em T033."""
    return create_agent(
        model=f"openai:{settings.openai_model}",
        tools=[],
        system_prompt=SYSTEM_PROMPT,
    )
