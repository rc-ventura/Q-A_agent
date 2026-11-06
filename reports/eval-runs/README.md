# Registro das medições da bateria de eval (fase 7)

Saídas completas do `pytest -m eval -v` em 2026-11-06, no commit indicado, uma rodada por vez e sem o
app rodando ao mesmo tempo (uma rodada concorrente anterior foi descartada por contaminação).

| Arquivo | Estado do código | Resultado | Falhas |
|---|---|---|---|
| `2026-11-06-round-1.txt` | temperatura padrão do modelo; prompt do dispatcher com a regra "nunca responda vou encaminhar" | 41/43 em 4 min 11 s | `unknown_customer_is_not_invented`, `accessory_redirects_to_instruments` |
| `2026-11-06-round-2.txt` | idem, com ajuste de prompt de pedidos e asserção ampliada | 41/43 em 4 min 01 s | `golden7-black-friday-inativa`, `golden8_mixed_price_and_installments` |
| `2026-11-06-round-3.txt` | temperatura 0 | 43/43 em 4 min 08 s | nenhuma |
| `2026-11-06-round-4.txt` | temperatura 0 | 43/43 em 3 min 46 s | nenhuma |

## Medições isoladas (10 execuções por caso, saída apenas no terminal da sessão; não há arquivo)

Resultados que o README cita, anotados aqui na ordem em que foram medidos:

- Frete para Manaus: 9/10 antes do ajuste de prompt; 4/10 com a primeira redação do ajuste (o agente deixava de citar
  o CEP); 10/10 com a redação final.
- `lgpd-exclusao`, `unknown_customer`, `accessory`, `golden7-black-friday-inativa` e `golden8`: 10/10 cada, em
  execução isolada, após falharem uma vez na bateria completa.
- PIX sobre promoção com temperatura 0: 20/20 (com a temperatura padrão, 14/18 numa medição anterior).

Essas medições isoladas não têm arquivo de saída e são atestadas pelo autor; as quatro rodadas completas acima têm.
