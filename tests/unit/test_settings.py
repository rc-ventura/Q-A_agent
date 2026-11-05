from agent.settings import Settings


def test_defaults(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    s = Settings()
    assert s.openai_model == "gpt-4o-mini"
    assert s.openai_api_key is None
    assert s.rag_min_score == 0.25


def test_env_override(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    s = Settings()
    assert s.openai_api_key == "sk-test"
    assert s.openai_model == "gpt-4o"


def test_paths_derived(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    s = Settings()
    assert s.source_dir.name == "source"
    assert s.runtime_dir.name == "runtime"
    assert s.store_db_path.suffix == ".db"
    assert s.checkpoint_db_path.suffix == ".db"
    assert "chroma" in str(s.chroma_dir)
