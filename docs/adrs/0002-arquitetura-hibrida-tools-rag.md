# ADR-0002: Arquitetura hibrida — function calling sobre SQLite + RAG ChromaDB

## Status

Aceito (2026-11-04). O item "harness deepagents com tools podados" e suprimido
pelo ADR-0003 (`create_agent`); a arquitetura hibrida tools+RAG permanece
integral.

## Contexto

O desafio pede explicitamente que o agente "saiba quando consultar dados
(disponibilidade, precos, status de pedido) e quando consultar politicas (regras
de troca, horarios, formas de pagamento)". As fontes tem naturezas diferentes:

- Dados operacionais: 6 CSVs tabulares (produtos, categorias, pedidos, itens,
  clientes, promocoes) — exigem filtros, ordenacao e calculo deterministico
  (preco final com desconto, estoque, pedidos por cliente).
- Politicas: um manual em PDF (~8 paginas, ~3,5 mil palavras) — texto corrido
  estruturado por secoes numeradas.

Alternativas consideradas: RAG puro sobre tudo (incluindo CSVs), agente SQL
gerando queries livremente, prompt-stuffing do PDF inteiro no system prompt.

## Decisao

Arquitetura hibrida sobre o harness `deepagents` (LangChain, runtime LangGraph),
com o conjunto de tools embutidos podado (sem filesystem/shell — ataque de
prompt injection via mensagem do cliente) e tres classes de tools de dominio,
read-only:

1. Tools de catálogo/pedidos: function calling com SQL parametrizado sobre
   SQLite (`store.sqlite`, ingerido dos CSVs com validacao Pydantic). Query
   deterministica devolve exatamente o que esta na fonte — requisito SC-001
   (100% de fidelidade, zero valores inventados).
2. Tool de politicas: RAG com ChromaDB persistente local, chunking por secao do
   manual (nao por tamanho fixo), metadados `{section_no, section_title, page}`,
   top-k=3 com score minimo configuravel (default 0.25), retorno de texto bruto
   sem sumarizacao. Weak retrieval retorna marcador explicito para o agente
   degradar honestamente (FR-011) em vez de alucinar regra.
3. Tool institucional fixo (`get_store_info`): dados estaveis (endereco,
   horarios, telefone) sem round de retrieval.

O design do RAG e balizado pelos sete pontos de falha de Barnett et al. 2024
("Seven Failure Points When Engineering a Retrieval Augmented Generation
System", arXiv:2401.05856): FP1 mitigado por score minimo + degradacao honesta;
FP2/FP6 por chunking por secao com listas/condicoes completas; FP3/FP4 por
retorno de texto bruto; FP5 por contrato de formato no system prompt; FP7 por
secoes integrais e bateria de teste.

## Consequencias

Positivas:

- Separacao fiel ao enunciado ("dados vs. politicas") e visivel na UI (cada
  tool call aparece como bloco distinto — criterio de avaliacao do desafio).
- Filtros e calculos sobre dados tabulares sao deterministicos e testaveis
  (pytest unitario sem LLM).
- RAG sofre onde RAG e a ferramenta certa (texto de regras com excecoes),
  com mitigaçao documentada dos modos de falha classicos.

Negativas:

- Duas bases de conhecimento para manter (SQLite e Chroma) — custo de
  complexidade aceito em troca de precisao.
- Ingestao do PDF depende de chave OpenAI (embeddings text-embedding-3-small)
  no primeiro acesso — tratado pelo onboarding da UI antes de liberar o chat.
- Substituir o provedor de embeddings exige reingestao (IDs deterministicos
  tornam a operacao idempotente).

Fonte racional completa: `specs/001-store-qa-agent/research.md` (D1 e D4).
