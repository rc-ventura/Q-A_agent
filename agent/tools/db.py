from agent.db import connect_readonly


def open_readonly(path):
    """Abre o SQLite operacional em modo read-only (contrato dos tools)."""
    return connect_readonly(path)
