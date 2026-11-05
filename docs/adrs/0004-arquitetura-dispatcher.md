# ADR-0004: Arquitetura dispatcher — roteador + especialistas por dominio

## Status

Aceito (2026-11-04). Suprime a decisao single-agent de research.md D9 (que vira
o documentado alternativo) e compoe com ADR-0003 (harness = `create_agent` por
agente, dispatcher e especialistas).

## Contexto

O desafio pede explicitamente que o agente "saiba quando consultar dados
(preco, estoque, pedido) e quando consultar politicas (trocas, horarios,
pagamento)". O autor decidiu demonstrar esse roteamento de forma explicita e
estrutural — nao apenas implicita na selecao de tools — e alinhar o numero de
agentes as user stories da spec (cada dominio = uma unidade testavel).

## Decisao

Arquitetura **dispatcher** (supervisor/roteador leve), composta de
`create_agent` por agente — sem dependencias extras de multi-agente:

- **Dispatcher**: `create_agent` com o system prompt de persona/escopo e com 4
  tools-roteadoras, uma por especialista. O dispatcher NUNCA toca dados ou
  politicas diretamente — delega.
- **Especialistas** (1:1 com as user stories, cada um um `create_agent` com
  prompt e tools do dominio):
  - `catalog_agent` (US1): `search_products`, `get_product_details`
  - `policies_agent` (US2): `search_policies`, `get_store_info`
  - `orders_agent` (US3): `find_customer`, `list_customer_orders`
  - `service_agent` (US4): persona/escopo/reclamacoes (sem tools de dados;
    responde saudacao, fora de escopo, redirecionamentos)
- Estado compartilhado: `checkpointer` por thread no grafo raiz (dispatcher);
  especialistas sao stateless por chamada.
- Cada especialista e compilavel e testavel isoladamente (unit) e via bateria
  eval (por dominio), preservando a independencia das user stories.

Implementacao: cada especialista e um grafo compilado encapsulado num tool do
dispatcher (a tool recebe a pergunta do usuario e devolve a resposta textual do
especialista). Roteamento visivel na UI como tool call por dominio — criterio
de avaliacao do enunciado.

## Consequencias

Positivas:

- Roteamento dados-vs-politicas explicito e estruturalmente visivel (nao so no
  prompt): o avaliador ve o dispatcher delegando ao especialista correto.
- Prompts por dominio curtos e focados (menos conflito entre tom de venda e
  estrito cumprimento de regras — mitiga FP5/FP6 do paper de referencia).
- Testabilidade por dominio identica a independencia das user stories.
- Evolucao natural: trocar um especialista nao toca os demais; modelo por
  dominio viavel depois (barato p/ chit-chat).

Negativas:

- +1 hop de LLM por turno (latencia ~1s) e custo do prompt do dispatcher.
- Duas camadas de tool calling: falhas de roteamento possiveis (dispatcher
  chuta especialista errado) — mitigacao: descricoes das ferramentas-roteador
  declarativas + eval de rota por dominio.
- Mais superficie de teste (dispatcher + 4 especialistas).

Fonte: research.md D9; decisao do autor de 2026-11-04 ("monte com a
arquitetura dispatcher").
