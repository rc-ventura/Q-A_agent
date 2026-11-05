from langchain.agents import create_agent

from agent.settings import Settings

SYSTEM_PROMPT = """Especialista de atendimento da Emporio da Musica (saudacoes, reclamacoes, pedidos fora de escopo).
Responda em portugues do Brasil, curto, cordial e empatico.
Nao responda sobre produtos, precos, pedidos ou politicas: peca ao dispatcher para rotear ao especialista correto.
Para reclamacoes e casos nao resolvidos, ofereca o telefone/WhatsApp (67) 3341-4444."""


def build(settings: Settings):
    """Especialista de atendimento (US4): sem tools de dados por design (ADR-0004)."""
    return create_agent(
        model=f"openai:{settings.openai_model}",
        tools=[],
        system_prompt=SYSTEM_PROMPT,
    )
