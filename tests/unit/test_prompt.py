from agent.prompt import DISPATCHER_SYSTEM_PROMPT
from agent.specialists.catalog_agent import SYSTEM_PROMPT as CATALOG
from agent.specialists.orders_agent import SYSTEM_PROMPT as ORDERS
from agent.specialists.policies_agent import SYSTEM_PROMPT as POLICIES
from agent.specialists.service_agent import SYSTEM_PROMPT as SERVICE


def test_dispatcher_markers():
    assert "Empório da Música" in DISPATCHER_SYSTEM_PROMPT
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
    for marker in ["escopo", "24 horas", "acessorios", "transacional", "esclarecimento"]:
        assert marker in SERVICE.lower(), marker


def test_dispatcher_always_delegates_and_covers_mixed_questions():
    prompt = DISPATCHER_SYSTEM_PROMPT.lower()
    assert "sempre delegue" in prompt
    assert "mista" in prompt and "todos os especialistas" in prompt
    assert "responda voce mesmo" not in prompt
    assert "frete" in prompt and "parcelamento" in prompt


def test_catalog_handles_discontinued_and_upcoming_products():  # manual 7.3
    for marker in ["descontinuado", "nao faz mais parte do catalogo", "em breve"]:
        assert marker in CATALOG.lower(), marker


def test_catalog_always_reports_stock_and_handles_named_campaigns():
    prompt = CATALOG.lower()
    for marker in ["sempre", "unidades em estoque", "campanha", "nao esta vigente"]:
        assert marker in prompt, marker


def test_orders_identifies_by_name_or_email_never_phone_and_never_guesses_quantity():  # FR-005, LGPD
    prompt = ORDERS.lower()
    for marker in ["nome completo ou e-mail", "nunca peca telefone", "quantity"]:
        assert marker in prompt, marker
    assert "nome/telefone" not in prompt


def test_dispatcher_never_offers_accessories():  # FR-008
    prompt = DISPATCHER_SYSTEM_PROMPT.lower()
    assert "nunca ofereca" in prompt and "acessorios" in prompt.split("nunca ofereca")[1][:80]
