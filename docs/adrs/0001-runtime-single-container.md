# ADR-0001: Runtime single container in-process em vez de LangGraph Server oficial

## Status

Aceito (2026-11-04), **ampliado em 2026-11-04**: mantido como **modo A**
(primario, caminho do avaliador). O modo B — Agent Server do blueprint oficial
(`langgraph build` + stack Postgres/Redis + agent-chat-ui) — passa a ser opcao
documentada/executavel de escala, nao mais apenas upgrade path teorico
(ver research.md D9 e ADR-0003). As razoes abaixo continuam validas para o
modo A; as do modo B sao sua compensacao quando a escala for exigida.

## Contexto

O desafio exige um agente de atendimento em Python e deixa framework, runtime,
persistencia e interface a criterio do autor (justificando no README). Duas
arquiteturas eram viveis com o blueprint LangChain/LangGraph:

- A) Runtime in-process: o processo Python serve a UI (Gradio) e invoca o grafo
  compilado diretamente, com checkpointer SQLite (`AsyncSqliteSaver`).
- B) LangGraph Server oficial (`langgraph build`/`up`): servidor de agentes em
  container dedicado, com APIs prontas de threads/runs/streaming.

Restricoes do projeto (definidas pelo autor): agente minimo, SQLite para longo
prazo, minimo de servicos e minima friccao para o avaliador (uma unica chave de
API).

## Decisao

Escolhida a opcao A — runtime in-process em um unico container Docker, servindo
UI e agente no mesmo processo, com `AsyncSqliteSaver` para checkpoints.

O projeto mantem o layout do blueprint oficial (`langgraph.json` apontando para
`agent/graph.py:graph`), de modo que `langgraph dev` funciona para desenvolvimento
(hot reload, Studio) e `langgraph build` permanece disponivel como caminho de
escalacao documentado.

## Consequencias

Positivas:

- Um unico container e um unico servico no compose (simplicidade operacional).
- SQLite viavel em ambas as finalidades (dados operacionais e checkpoints).
- Avaliador precisa de uma unica chave (OpenAI); nenhuma chave LangSmith exigida.
- Setup do zero ate a primeira conversa cabe no teto de 15 minutos (SC-006).

Negativas:

- Sem as APIs prontas de threads/runs/SSE do LangGraph Server; UI conversa
  diretamente com o grafo in-process (aceitavel para prototipo single-user).
- Escala horizontal exigiria migrar para o server oficial (caminho documentado
  via `langgraph.json` ja compativel; trocaria SQLite por Postgres).
- A API de streaming exposta a UI e propria do Gradio, nao a do server.

Referencias: docs.langchain.com/langsmith/local-dev-testing (tabela `langgraph dev`
vs `langgraph up`), docs.langchain.com/langsmith/deploy-standalone-server
(requisitos de Postgres/Redis/licenca), referencia interna AgendAI (stack de 6
servicos — o que este projeto deliberadamente simplifica).
