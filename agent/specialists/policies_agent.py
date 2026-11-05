from langchain.agents import create_agent

from agent.settings import Settings

SYSTEM_PROMPT = """Especialista em politicas da Emporio da Musica.
Responda em portugues do Brasil, curto e cordial.
Responda SEMPRE com base nos chunks do manual recuperados pelos tools; nao improvise regra.
Se a recuperacao nao trouxer o trecho relevante, diga que nao tem a informacao e ofereca o canal humano."""


def build(settings: Settings):
    """Especialista de politicas (US2): tools search_policies/get_store_info entram em T029."""
    return create_agent(
        model=f"openai:{settings.openai_model}",
        tools=[],
        system_prompt=SYSTEM_PROMPT,
    )
