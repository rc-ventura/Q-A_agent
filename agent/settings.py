from functools import cached_property
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Configuracao da aplicacao via .env/ambiente.

    Carrega chave do LLM (opcional ate o onboarding da UI), modelo OpenAI,
    limiar de score do RAG e deriva os caminhos de dados a partir da raiz
    do projeto: CSVs fonte em ``data/source`` e artefatos de execucao
    (banco de operacoes, checkpoints, indice vetorial) em ``data/runtime``.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    rag_min_score: float = 0.25

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
