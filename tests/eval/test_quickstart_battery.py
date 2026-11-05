import uuid

import pytest

from tests.eval.support import assert_reply, price, requires_real_key

pytestmark = [pytest.mark.eval, requires_real_key]

UNAVAILABLE = ("esgot", "indispon", "sem estoque", "fora de estoque", "não temos", "não há")
NOT_IN_FORCE = ("não está", "não há", "não temos", "encerrad", "expirad", "venc", "não é mais", "não estão")

CATALOG_CASES = [
    pytest.param(
        "Quais opções de violões disponíveis custando até R$1000?",
        ["yamaha c40", price(599.9)],
        ["takamine"],
        id="golden1-violoes-ate-1000",
    ),
    pytest.param("Quanto custa o Takamine GD20?", [price(2199.0), "5"], [], id="golden2-takamine-gd20"),
    pytest.param("Qual o preço da Gibson Les Paul Standard '50s e quantas tem?", [price(18900.0), "2"], [], id="gibson-preco-estoque"),
    pytest.param("O violão Giannini GF-3D está disponível?", [UNAVAILABLE], [], id="giannini-sem-estoque"),
    pytest.param(
        "Tem promoção no ukulele Kalani KAL-700T Tenor?",
        [price(359.0), "10%", price(323.1)],
        [],
        id="promocao-original-percentual-final",
    ),
    pytest.param(
        "Tem a promoção de Black Friday ainda?",
        [NOT_IN_FORCE],
        [],
        id="golden7-black-friday-inativa",
    ),
    pytest.param("Qual o ukulele mais barato que vocês têm?", [price(159.9), "shelby"], [], id="ukulele-mais-barato"),
    pytest.param(
        "Quais baterias acústicas Yamaha vocês têm?",
        ["kit 1", price(4439.0), "kit 3", price(14922.0)],
        [],
        id="baterias-yamaha",
    ),
    pytest.param(
        "Vocês ainda vendem o Ibanez Bass 2X?",
        [("descontinuad", "não faz mais parte", "não está mais", "não é mais")],
        [],
        id="baixo-descontinuado",
    ),
    pytest.param(
        "Tem algum teclado sintetizador até R$ 2000?",
        ["korg", price(1127.0)],
        [],
        id="teclado-ate-2000",
    ),
    pytest.param("Quantas unidades do Martin D-28E vocês têm?", [("1 unidade", "uma unidade", "apenas 1", "última")], [], id="martin-ultima-unidade"),
]

POLICY_CASES = [
    pytest.param(
        "Qual o horário de funcionamento da loja?",
        ["18", "13", "sábado"],
        [],
        id="horario",
    ),
    pytest.param("Qual o endereço da loja?", ["rua 14 de maio", "3200"], [], id="golden3-endereco"),
    pytest.param(
        "Me arrependi da minha compra, posso devolver meu pedido?",
        [("7 dias", "sete dias", "7 (sete)"), "embalagem original", "10 dias úteis", "frete"],
        [],
        id="golden4-arrependimento",
    ),
    pytest.param("Vocês dão desconto no PIX?", ["5%"], [], id="pix-desconto"),
    pytest.param("Posso parcelar em até quantas vezes?", [("12x", "12 vezes"), "100"], [], id="parcelamento"),
    pytest.param("Qual o valor do frete em Campo Grande?", ["500", "35"], [], id="frete-campo-grande"),
    pytest.param("O produto veio com defeito, em quanto tempo posso trocar?", ["30"], [], id="troca-defeito"),
    pytest.param("Qual a garantia legal dos produtos?", ["90"], [], id="garantia-legal"),
    pytest.param("Quanto tempo leva a entrega pelo PAC dos Correios?", [("5 a 12", "5 e 12")], [], id="prazo-pac"),
    pytest.param(
        "Como peço a exclusão dos meus dados pessoais?",
        ["exclus", ("whatsapp", "e-mail", "email", "contato")],
        [],
        id="lgpd-exclusao",
    ),
    pytest.param("Posso trocar por outra cor depois de comprar?", ["7"], [], id="troca-preferencia"),
    pytest.param("Dá pra trocar a boquilha de um sax que comprei?", ["higiene", "não"], [], id="boquilha-nao-elegivel"),
]


@pytest.mark.parametrize("question,required,forbidden", CATALOG_CASES)
def test_catalog_questions(agent, question, required, forbidden):
    assert_reply(agent.ask(question), required, forbidden)


@pytest.mark.parametrize("question,required,forbidden", POLICY_CASES)
def test_policy_questions(agent, question, required, forbidden):
    assert_reply(agent.ask(question), required, forbidden)


def test_golden5_orders_with_cancellation_reason(agent):
    reply = agent.ask("Sou Pedro Henrique Oliveira, cadê meu pedido?")
    assert_reply(
        reply,
        required=["brab1234567br", "cancelad", "pagamento"],
        forbidden=["7 unidades"],
    )


def test_order_lookup_asks_for_name_or_email_never_phone(agent):
    reply = agent.ask("Cadê meu pedido?")
    assert_reply(reply, required=[("nome", "e-mail", "email")], forbidden=["telefone"])


def test_unknown_customer_is_not_invented(agent):
    reply = agent.ask("Sou Zeferino Quintanilha Albuquerque, cadê meu pedido?")
    assert_reply(
        reply,
        required=[("não encontr", "não localizei", "não consegui", "confirmar", "e-mail", "fornecer")],
        forbidden=["brab1234567br", "brdz4561230br", "delivered", "entregue"],
    )


def test_golden6_accessory_redirect(agent):
    reply = agent.ask("Vocês vendem cordas avulsas?")
    assert_reply(reply, required=["instrumento"])


def test_golden8_mixed_price_and_installments(agent):
    reply = agent.ask("Quanto custa o Taylor 214ce e dá pra parcelar em 12x?")
    assert_reply(reply, required=[price(7499.0), ("12x", "12 vezes"), "sem juros"])


def test_followup_resolves_anaphoric_reference(agent):
    thread = uuid.uuid4().hex
    assert_reply(agent.ask("Quanto custa o Yamaha FG800?", thread), required=[price(1299.0)])
    reply = agent.ask("e o mais barato de nylon?", thread)
    assert_reply(reply, required=[("tagima memphis", price(429.9)[0])])


def test_followup_stock_after_price(agent):
    thread = uuid.uuid4().hex
    assert_reply(agent.ask("Quanto custa o Takamine GD20?", thread), required=[price(2199.0)])
    assert_reply(agent.ask("E quantas unidades tem em estoque?", thread), required=["5"])


def test_vague_request_resolved_within_two_exchanges(agent):
    thread = uuid.uuid4().hex
    agent.ask("Quero um violão para meu filho iniciante", thread)
    reply = agent.ask("Meu orçamento é até R$ 500", thread)
    assert_reply(reply, required=[(price(429.9)[0], price(459.9)[0])])
