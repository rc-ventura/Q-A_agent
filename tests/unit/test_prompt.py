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


def test_dispatcher_complaints_state_24h_return_and_preserve_specialist_details():  # manual 7.3
    prompt = DISPATCHER_SYSTEM_PROMPT.lower()
    assert "reclamac" in prompt and "24 horas uteis" in prompt
    assert "preserve" in prompt and "prazos" in prompt


def test_dispatcher_separates_complaints_from_policy_questions():
    prompt = DISPATCHER_SYSTEM_PROMPT.lower()
    assert "sem perguntar" in prompt
    assert "arrependimento" in prompt and "defeito" in prompt
    assert "delegue tambem a politicas" in prompt


def test_catalog_answers_named_campaign_in_first_sentence():
    """Medido: 8/10 sem a regra; o modelo respondia com outra promocao e nunca dizia que a campanha nao vige."""
    prompt = CATALOG.lower()
    assert "primeira frase" in prompt
    assert "nao esta vigente" in prompt


def test_dispatcher_keeps_conditions_when_merging_answers():
    """Medido: 'sem juros' sumia na recomposicao de pergunta mista (8/10)."""
    prompt = DISPATCHER_SYSTEM_PROMPT.lower()
    assert "sem juros" in prompt and "parcela minima" in prompt


def test_dispatcher_always_calls_policies_when_payment_terms_are_mentioned():
    """Medido: perguntas de produto + parcelamento/PIX saiam so com o catalogo em ~2 de 10 rodadas."""
    prompt = DISPATCHER_SYSTEM_PROMPT.lower()
    assert "mesmo que" in prompt
    for term in ["parcelar", "pix", "frete"]:
        assert term in prompt, term


def test_policies_offers_human_contact_when_a_specific_quote_is_not_in_the_manual():
    # Eval: o manual explica COMO o frete e calculado, mas nao traz o valor para uma cidade.
    # Sem esta regra o agente as vezes parava na explicacao e omitia o contato da equipe.
    prompt = POLICIES.lower()
    assert "cotacao" in prompt
    assert "mesmo que o manual explique" in prompt
    assert "3341-4444" in prompt


def test_dispatcher_never_narrates_a_handoff_instead_of_calling_the_specialist():
    # Eval: em rodadas isoladas o roteador respondeu "vou encaminhar, um momento" sem chamar a tool.
    prompt = DISPATCHER_SYSTEM_PROMPT.lower()
    assert "um momento" in prompt
    assert "na mesma resposta" in prompt


def test_orders_asks_for_email_when_no_customer_is_found():
    # Eval: com cliente desconhecido o agente as vezes pedia "cidade ou outro nome" em vez do e-mail.
    prompt = ORDERS.lower()
    assert "nenhum candidato" in prompt
    assert "e-mail" in prompt.split("nenhum candidato", 1)[1]
