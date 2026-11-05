from langchain.agents import create_agent

from agent.settings import Settings

SYSTEM_PROMPT = """Especialista em catalogo da Emporio da Musica.
Responda em portugues do Brasil, curto e cordial.
Consulte SEMPRE os tools de catalogo para preco, estoque, promocao e detalhes.
Nunca invente valores: se o tool nao retornar, diga que nao localizou.
Nao venda acessorios (cordas, palhetas, cabos, cases, pedais, amplificadores): a loja vende instrumentos."""


def build(settings: Settings):
    """Especialista de catalogo (US1): tools de busca/detalhe entram em T026."""
    return create_agent(
        model=f"openai:{settings.openai_model}",
        tools=[],
        system_prompt=SYSTEM_PROMPT,
    )
