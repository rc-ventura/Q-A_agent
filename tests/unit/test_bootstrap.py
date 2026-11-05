import csv
import sqlite3
from types import SimpleNamespace

import httpx
import openai

from app import bootstrap
from app.bootstrap import activate_key, check_api_key, ensure_data

SOURCE = bootstrap.Settings(_env_file=None).source_dir


class FakeClient:
    def __init__(self, error=None):
        self.models = SimpleNamespace(list=self._list)
        self.error = error

    def _list(self):
        if self.error:
            raise self.error


def request():
    return httpx.Request("GET", "https://api.openai.com/v1/models")


def test_check_api_key_empty():
    assert "informe" in check_api_key("   ", client_factory=lambda k: FakeClient()).lower()


def test_check_api_key_valid_returns_none():
    assert check_api_key("sk-ok", client_factory=lambda k: FakeClient()) is None


def test_check_api_key_rejected_by_provider():
    error = openai.AuthenticationError(
        "Incorrect API key sk-proj-xyz", response=httpx.Response(401, request=request()), body=None
    )
    message = check_api_key("sk-proj-xyz", client_factory=lambda k: FakeClient(error))
    assert "inválida" in message.lower()
    assert "sk-proj-xyz" not in message


def test_check_api_key_provider_unreachable_is_not_reported_as_invalid():
    error = openai.APIConnectionError(request=request())
    message = check_api_key("sk-ok", client_factory=lambda k: FakeClient(error))
    assert "inválida" not in message.lower()
    assert "validar" in message.lower()


def test_ensure_data_ingests_and_indexes_idempotently(tmp_path, monkeypatch):
    indexed = []
    monkeypatch.setattr(bootstrap, "index_policies", lambda s: indexed.append(s))
    settings = SimpleNamespace(
        runtime_dir=tmp_path / "runtime",
        store_db_path=tmp_path / "runtime" / "store.db",
        source_dir=SOURCE,
    )
    ensure_data(settings)
    ensure_data(settings)
    conn = sqlite3.connect(settings.store_db_path)
    products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    conn.close()
    with open(SOURCE / "products.csv", newline="", encoding="utf-8") as fh:
        expected = sum(1 for _ in csv.DictReader(fh))
    assert products == expected
    assert len(indexed) == 2


def test_activate_key_invalid_does_not_save_or_prepare():
    calls = []
    message = activate_key(
        "ruim",
        settings=object(),
        check=lambda k: "Chave inválida.",
        save=lambda k: calls.append("save"),
        prepare=lambda s: calls.append("prepare"),
    )
    assert message == "Chave inválida."
    assert calls == []


def test_activate_key_valid_saves_then_prepares():
    calls = []
    settings = object()
    message = activate_key(
        "  sk-ok  ",
        settings=settings,
        check=lambda k: None,
        save=lambda k: calls.append(("save", k)),
        prepare=lambda s: calls.append(("prepare", s)),
    )
    assert message is None
    assert calls == [("save", "sk-ok"), ("prepare", settings)]


def test_activate_key_prepare_failure_returns_clear_message_without_details():
    def boom(_):
        raise RuntimeError("detalhe interno com sk-ok")

    message = activate_key(
        "sk-ok", settings=object(), check=lambda k: None, save=lambda k: None, prepare=boom
    )
    assert "dados" in message.lower()
    assert "sk-ok" not in message
