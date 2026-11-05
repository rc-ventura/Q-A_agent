from agent.prompt import DISPATCHER_SYSTEM_PROMPT
from agent.specialists.catalog_agent import SYSTEM_PROMPT as CATALOG
from agent.specialists.orders_agent import SYSTEM_PROMPT as ORDERS
from agent.specialists.policies_agent import SYSTEM_PROMPT as POLICIES
from agent.specialists.service_agent import SYSTEM_PROMPT as SERVICE


def test_dispatcher_markers():
    assert "Emporio da Musica" in DISPATCHER_SYSTEM_PROMPT
    assert "Nunca invente" in DISPATCHER_SYSTEM_PROMPT  # FR-002
    assert "fora do escopo" in DISPATCHER_SYSTEM_PROMPT  # FR-009
    assert "transacionais" in DISPATCHER_SYSTEM_PROMPT  # FR-012
    assert "(67) 3341-4444" in DISPATCHER_SYSTEM_PROMPT


def test_catalog_promotion_format():  # FR-006 + US1 T026
    for marker in ["preco original", "percentual", "preco final",
                   "transparente", "sem estoque", "alternativas"]:
        assert marker in CATALOG.lower(), marker


def test_policies_only_from_manual():  # FR-003 + FR-011 (T030)
    for marker in ["chunks", "improvise", "literalmente", "weak", "(67) 3341-4444"]:
        assert marker in POLICIES.lower(), marker


def test_orders_no_transactions_and_human_escalation():  # FR-012 + FR-005 (T034)
    for marker in ["transacionais", "(67) 3341-4444", "esclarecimento", "notes"]:
        assert marker in ORDERS.lower(), marker


def test_service_scope():
    assert "escopo" in SERVICE.lower()
