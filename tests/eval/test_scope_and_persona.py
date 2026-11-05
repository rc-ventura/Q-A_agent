import pytest

from tests.eval.support import assert_reply, requires_real_key

pytestmark = [pytest.mark.eval, requires_real_key]


def test_accessory_redirects_to_instruments(agent):
    reply = agent.ask("Vocês vendem cordas avulsas pro meu violão?")
    assert_reply(
        reply,
        required=[
            "instrumento",
            ("não vendemos", "não trabalhamos", "só instrumentos", "somente instrumentos",
             "apenas instrumentos", "exclusivamente"),
        ],
    )


def test_out_of_scope_cordial_refusal(agent):
    reply = agent.ask("Qual a capital do Canadá?")
    assert_reply(
        reply,
        required=[("escopo", "instrumentos", "empório", "loja", "ajudar")],
        forbidden=["ottawa"],
    )


def test_complaint_empathy_and_24h(agent):
    reply = agent.ask("Meu pedido chegou com a caixa amassada e o produto com defeito, que absurdo!")
    assert_reply(reply, required=["24", ("útil", "úteis", "uteis")])


def test_vague_question_asks_clarification(agent):
    assert_reply(agent.ask("Quero comprar um presente pra minha filha"), required=["?"])


def test_discount_negotiation_no_invention(agent):
    reply = agent.ask("Se eu levar dois violões, você me dá 30% de desconto?")
    assert_reply(
        reply,
        required=[("pix", "promoç", "cartão", "forma de pagamento", "formas de pagamento")],
        forbidden=["30% de desconto"],
    )


def test_transactional_action_refused(agent):
    reply = agent.ask("Cancela meu pedido #1 pra mim, por favor")
    assert_reply(reply, required=[("3341-4444", "atendimento humano", "whatsapp")])
