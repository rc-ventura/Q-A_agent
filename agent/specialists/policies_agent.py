from langchain.agents import create_agent

from agent.settings import Settings
from agent.tools.policies import make_policies_tools

SYSTEM_PROMPT = """Especialista em politicas da Emporio da Musica.
Responda em portugues do Brasil, curto e cordial.
Responda SEMPRE com base nos chunks do manual recuperados pelos tools; nao improvise regra.
Se a recuperacao retornar retrieval=weak ou nao trouxer o trecho relevante, declare o limite e ofereca o canal humano (67) 3341-4444.
Ao citar prazos, valores e condicoes, repita literalmente o trecho do manual; nunca responda politica de cabeca."""


def build(settings: Settings, collection=None):
    """Especialista de politicas (US2) com tools do manual (T029/T030)."""
    return create_agent(
        model=f"openai:{settings.openai_model}",
        tools=make_policies_tools(settings, collection=collection),
        system_prompt=SYSTEM_PROMPT,
    )
