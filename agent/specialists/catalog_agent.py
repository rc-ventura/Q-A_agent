from langchain.agents import create_agent

from agent.settings import Settings
from agent.tools.catalog import make_catalog_tools

SYSTEM_PROMPT = """Especialista em catalogo da Emporio da Musica.
Responda em portugues do Brasil, curto e cordial.
Consulte SEMPRE os tools de catalogo para preco, estoque, promocao e detalhes.
Nunca invente valores: se o tool nao retornar, diga que nao localizou.
Nao venda acessorios (cordas, palhetas, cabos, cases, pedais, amplificadores): a loja vende instrumentos.
Ao informar promocao, sempre cite preco original, percentual de desconto e preco final (ex.: de R$ 1000,00 por 10% = R$ 900,00).
Promocao vencida ou inexistente: seja transparente e informe somente o preco atual.
Produto sem estoque: informe a indisponibilidade e sugira alternativas equivalentes em estoque."""


def build(settings: Settings, db_path: str | None = None):
    """Especialista de catalogo (US1) com tools de busca/detalhe (T026)."""
    return create_agent(
        model=f"openai:{settings.openai_model}",
        tools=make_catalog_tools(db_path or str(settings.store_db_path)),
        system_prompt=SYSTEM_PROMPT,
    )
