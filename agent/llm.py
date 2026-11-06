from langchain.chat_models import init_chat_model

from agent.settings import Settings


def build_model(settings: Settings):
    """Modelo de chat do dispatcher e dos especialistas, com temperatura configuravel (padrao 0)."""
    return init_chat_model(f"openai:{settings.openai_model}", temperature=settings.openai_temperature)
