import logging
import sqlite3
from collections.abc import Callable

import openai
from openai import OpenAI

from agent.ingest import ingest_all
from agent.policies_rag import index_policies
from agent.settings import Settings, save_api_key

logger = logging.getLogger(__name__)

INVALID_KEY_MESSAGE = "Chave inválida ou sem permissão. Confira e tente de novo."


def _default_client(key: str) -> OpenAI:
    return OpenAI(api_key=key, timeout=15)


def check_api_key(key: str, client_factory: Callable[[str], OpenAI] = _default_client) -> str | None:
    """Valida a chave com uma chamada barata (listagem de modelos, sem tokens).

    Args:
        key: chave informada pelo usuario.
        client_factory: fabrica do cliente OpenAI (injetavel em testes).

    Returns:
        None quando a chave e aceita; senao mensagem pt-BR para exibir na tela.
        Falha de rede/servico nao e reportada como chave invalida. O texto da
        excecao nunca e incluido (pode ecoar a chave).
    """
    key = key.strip()
    if not key:
        return "Informe a chave da OpenAI."
    try:
        client_factory(key).models.list()
    except openai.AuthenticationError:
        return INVALID_KEY_MESSAGE
    except Exception as exc:
        logger.error("validacao da chave nao concluida: %s", type(exc).__name__)
        return "Não foi possível validar a chave agora (sem conexão ou serviço indisponível). Tente novamente."
    return None


def startup_key_state(
    key: str | None, check: Callable[[str], str | None] = check_api_key
) -> str:
    """Classifica a chave guardada na partida do app.

    Returns:
        ``missing`` sem chave; ``ok`` quando aceita; ``rejected`` quando a OpenAI a
        recusa; ``unverified`` quando a checagem nao concluiu (rede ou servico fora).
        Uma chave ``unverified`` nao deve mandar o usuario de volta ao onboarding:
        o problema e transitorio e o chat reporta qualquer falha real.
    """
    key = (key or "").strip()
    if not key:
        return "missing"
    error = check(key)
    if error is None:
        return "ok"
    return "rejected" if error == INVALID_KEY_MESSAGE else "unverified"


def ensure_data(settings) -> None:
    """Prepara os dados da loja: CSVs no SQLite e politicas no indice vetorial.

    Idempotente (upsert), entao roda a cada inicializacao sem duplicar nada.

    Args:
        settings: configuracao com ``runtime_dir``, ``store_db_path`` e ``source_dir``.

    Raises:
        pydantic.ValidationError: linha invalida em algum CSV de origem.
    """
    settings.runtime_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.store_db_path)
    try:
        ingest_all(settings.source_dir, conn)
    finally:
        conn.close()
    index_policies(settings)


def activate_key(
    key: str,
    *,
    settings: Settings,
    check: Callable[[str], str | None] = check_api_key,
    save: Callable[[str], None] = save_api_key,
    prepare: Callable[[Settings], None] = ensure_data,
) -> str | None:
    """Fluxo F0: valida a chave, grava no .env, ativa no processo e prepara os dados.

    Args:
        key: chave digitada na tela de configuracao.
        settings: configuracao da aplicacao.
        check: validador da chave (injetavel).
        save: persistencia da chave (injetavel).
        prepare: preparo dos dados (injetavel).

    Returns:
        None em caso de sucesso; senao a mensagem de erro a exibir, mantendo o
        usuario na tela de configuracao. A chave so e gravada se for valida.
    """
    key = key.strip()
    error = check(key)
    if error:
        return error
    save(key)
    try:
        prepare(settings)
    except Exception as exc:
        logger.error("preparo dos dados falhou: %s", type(exc).__name__)
        return "Chave válida, mas não consegui preparar os dados da loja. Veja os logs e tente novamente."
    return None
