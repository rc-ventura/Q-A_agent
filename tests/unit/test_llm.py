from agent.llm import build_model
from agent.settings import Settings


def test_model_is_deterministic_by_default(monkeypatch):
    # Atendimento nao precisa de criatividade: temperatura 0 reduz a variancia medida na bateria.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-unit-test")
    model = build_model(Settings())
    assert model.temperature == 0
    assert model.model_name == "gpt-4o-mini"


def test_temperature_and_model_come_from_settings(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-unit-test")
    model = build_model(Settings(openai_model="gpt-4o", openai_temperature=0.3))
    assert (model.model_name, model.temperature) == ("gpt-4o", 0.3)
