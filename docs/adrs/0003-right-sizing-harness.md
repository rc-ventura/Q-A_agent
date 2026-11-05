# ADR-0003: Right-sizing do harness — create_agent em vez de deepagents

## Status

Aceito (2026-11-04). Suprime parcialmente o ADR-0002: o item "harness deepagents
com tools podados" passa a ser `langchain.agents.create_agent`.

## Contexto

O desafio exige um agente de atendimento com loop LLM↔tools, RAG de politicas,
persona e controle de escopo. A decisao anterior (ADR-0002) adotava o harness
`deepagents` da LangChain com o conjunto de tools embutidos podado (filesystem,
subagentes, shell).

Reavaliacao por evidencia: o que o deepagents adiciona sobre um loop de
tool-calling (planejamento/todos, filesystem virtual, subagentes `task`,
`execute` shell, memoria de longo prazo) nao tem uso neste dominio — interacoes
de 1 a 3 passos, dados via SQLite/Chroma atras de tools, sem delegacao. O
allowlist minimo de filesystem do deepagents ainda exige `read_file` (overhead
de prompt), e as dependencias diretas (`langchain-anthropic`,
`langchain-google-genai`, `langsmith`) ficariam sem uso com provedor OpenAI.

`langchain.agents.create_agent` entrega o necessario: loop de tool-calling,
streaming, middleware e `checkpointer` nativos (assinatura verificada em
langchain 1.4.x instalado). Precedente: AgendAI usa `create_agent` com o mesmo
sistema de middleware.

## Decisao

Harness do agente = `create_agent` (langchain 1.4.7, pinada por maturidade
>=7 dias — 1.4.9 publicada no mesmo dia foi rejeitada). Layout do blueprint
(`langgraph.json`, `agent/graph.py:graph`) mantido. `deepagents` removido das
dependencias.

## Consequencias

Positivas:

- Zero superficie de ataque a podar: filesystem/subagentes/shell nao existem.
- Menos dependencias e menos tokens de prompt embutidos.
- Mesma API de `checkpointer` e middleware — nenhuma mudanca em tools, RAG,
  ingestao, SQLite, UI ou testes.

Negativas:

- Perde-se o upgrade "gratuito" para tarefas multi-passo (planejamento,
  artefatos); se surgir, deepagents vira dependencia incremental — ja esta
  documentado como upgrade path em research.md D1/D9.
- A narrativa muda de "harness oficial completo" para "right-sizing consciente"
  — para a avaliacao do desafio e um relato mais forte, nao mais fraco.

Referencias: research.md D1 (revisada) e D9 (multi-agente e modo blueprint);
verificacao de API via context7 e import local.
