STORE_INFO = {
    "nome": "Empório da Música",
    "razao_social": "Empório da Música Instrumentos Musicais Ltda.",
    "endereco": "Rua 14 de Maio, 3200 — Centro, Campo Grande - MS, CEP 79202-333",
    "telefone_whatsapp": "(67) 3341-4444",
    "email": "contato@emporiodamusica.com.br",
    "horario": {
        "segunda_a_sexta": "09:00 às 18:00",
        "sabado": "09:00 às 13:00",
        "domingo_e_feriados": "Fechado",
    },
    "fundacao": 2008,
}


def get_store_info() -> dict:
    """Dados institucionais estaveis da loja, verbatim do manual.

    Fonte: secoes 1 (Sobre/Dados da Empresa) e 2 (Horario de Funcionamento)
    do manual de politicas. Retorna sem round de retrieval por serem dados
    fixos (ADR-0002, item 3) — evita FP1/FP2 para informacao imutavel.
    """
    return dict(STORE_INFO)
