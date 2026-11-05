import os
from functools import cached_property
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Configuracao da aplicacao via .env/ambiente.

    Carrega chave do LLM (opcional ate o onboarding da UI), modelo OpenAI,
    limiar de score do RAG e deriva os caminhos de dados a partir da raiz
    do projeto: CSVs fonte em ``data/source`` e artefatos de execucao
    (banco de operacoes, checkpoints, indice vetorial) em ``data/runtime``.
    """

    model_config = SettingsConfigDict(env_file=_ROOT / ".env", extra="ignore")

    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    rag_min_score: float = 0.30

    @cached_property
    def source_dir(self) -> Path:
        """Diretorio dos CSVs/PDF fonte versionados (data/source)."""
        return _ROOT / "data" / "source"

    @cached_property
    def runtime_dir(self) -> Path:
        """Diretorio de artefatos de execucao ignorados pelo git (data/runtime)."""
        return _ROOT / "data" / "runtime"

    @cached_property
    def store_db_path(self) -> Path:
        """Caminho do SQLite operacional (produtos, pedidos, promocoes)."""
        return self.runtime_dir / "store.db"

    @cached_property
    def checkpoint_db_path(self) -> Path:
        """Caminho do SQLite de checkpoints de conversa (AsyncSqliteSaver)."""
        return self.runtime_dir / "checkpoints.db"

    @cached_property
    def chroma_dir(self) -> Path:
        """Diretorio do indice vetorial ChromaDB das politicas."""
        return self.runtime_dir / "chroma"


def get_settings() -> Settings:
    """Factory de Settings (ponto unico de injecao para testes)."""
    return Settings()


def save_api_key(key: str, env_path: Path | None = None) -> None:
    """Persiste a chave no .env local e a ativa no processo (onboarding F0).

    Substitui ou acrescenta a linha OPENAI_API_KEY preservando as demais,
    restringe o arquivo ao dono (0600) e nunca loga o valor.

    Args:
        key: chave da OpenAI, sem espacos nem quebras de linha.
        env_path: caminho do .env (padrao: raiz do projeto).

    Raises:
        ValueError: chave vazia ou com espacos/quebras (evita injetar linhas no .env).
    """
    if not key or any(c.isspace() for c in key):
        raise ValueError("chave de API malformada")
    env_path = env_path or (_ROOT / ".env")
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    entry = f"OPENAI_API_KEY={key}"
    if any(line.startswith("OPENAI_API_KEY=") for line in lines):
        lines = [entry if line.startswith("OPENAI_API_KEY=") else line for line in lines]
    else:
        lines.append(entry)
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    env_path.chmod(0o600)
    os.environ["OPENAI_API_KEY"] = key
