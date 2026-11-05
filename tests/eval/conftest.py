import sqlite3

import pytest

from agent.ingest import ingest_all
from agent.policies_rag import index_policies
from agent.settings import Settings
from tests.eval.support import Agent


@pytest.fixture(scope="session", autouse=True)
def store_ready():
    settings = Settings()
    settings.runtime_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.store_db_path)
    try:
        ingest_all(settings.source_dir, conn)
    finally:
        conn.close()
    index_policies(settings)


@pytest.fixture(scope="session")
def agent(store_ready):
    client = Agent()
    yield client
    client.close()
