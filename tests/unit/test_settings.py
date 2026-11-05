import os
import stat

import pytest

from agent.settings import Settings, save_api_key


def test_defaults(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    s = Settings(_env_file=None)
    assert s.openai_model == "gpt-4o-mini"
    assert s.openai_api_key is None
    assert s.rag_min_score == 0.30


def test_env_override(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    s = Settings(_env_file=None)
    assert s.openai_api_key.get_secret_value() == "sk-test"
    assert s.openai_model == "gpt-4o"


def test_api_key_is_masked_in_repr(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-segredo-123")
    assert "sk-segredo-123" not in repr(Settings(_env_file=None))


def test_paths_derived(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    s = Settings(_env_file=None)
    assert s.source_dir.name == "source"
    assert s.runtime_dir.name == "runtime"
    assert s.store_db_path.suffix == ".db"
    assert s.checkpoint_db_path.suffix == ".db"
    assert "chroma" in str(s.chroma_dir)


def test_save_api_key_creates_env_and_activates_process(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "antiga")
    env = tmp_path / ".env"
    save_api_key("sk-nova", env_path=env)
    assert env.read_text() == "OPENAI_API_KEY=sk-nova\n"
    assert os.environ["OPENAI_API_KEY"] == "sk-nova"


def test_save_api_key_replaces_line_and_preserves_others(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "antiga")
    env = tmp_path / ".env"
    env.write_text("OPENAI_MODEL=gpt-4o\nOPENAI_API_KEY=velha\nRAG_MIN_SCORE=0.3\n")
    save_api_key("sk-nova", env_path=env)
    assert env.read_text() == "OPENAI_MODEL=gpt-4o\nOPENAI_API_KEY=sk-nova\nRAG_MIN_SCORE=0.3\n"


def test_save_api_key_appends_when_absent(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "antiga")
    env = tmp_path / ".env"
    env.write_text("OPENAI_MODEL=gpt-4o\n")
    save_api_key("sk-nova", env_path=env)
    assert env.read_text() == "OPENAI_MODEL=gpt-4o\nOPENAI_API_KEY=sk-nova\n"


def test_save_api_key_restricts_file_permissions(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "antiga")
    env = tmp_path / ".env"
    save_api_key("sk-nova", env_path=env)
    assert stat.S_IMODE(env.stat().st_mode) & 0o077 == 0


@pytest.mark.parametrize("bad", ["", "   ", "sk-a\nOPENAI_MODEL=x", "sk a"])
def test_save_api_key_rejects_malformed_key(monkeypatch, tmp_path, bad):
    monkeypatch.setenv("OPENAI_API_KEY", "antiga")
    env = tmp_path / ".env"
    with pytest.raises(ValueError):
        save_api_key(bad, env_path=env)
    assert not env.exists()
    assert os.environ["OPENAI_API_KEY"] == "antiga"
