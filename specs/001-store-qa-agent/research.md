# Research: Agente de Atendimento Virtual — Empório da Música

**Data**: 2026-11-03 | **Spec**: [spec.md](./spec.md) | **Referência de arquitetura**: projeto AgendAI (do autor), repositório local

Fonte de verdade do escopo: `Desafio Técnico AI Engineer 2026 2/desafio_tecnico_ai_eng_artefact.pdf`.

Diretrizes do autor (superior a qualquer default): **Python + Pydantic; deepagents da LangChain; LangGraph como runtime; blueprint pronto da LangChain; containers Docker; Gradio (ou UI pronta da LangChain se precisar escalar); SQLite para longo prazo; RAG com ChromaDB local guiado pelo artigo de falhas de RAG; agente MÍNIMO (sem constelação de serviços); ênfase em decisões técnicas documentadas, trade-offs e edge cases.**

---

## D1 — Harness do agente: `create_agent` (right-sized)

**Decision (revisada 2026-11-04)**: Usar `langchain.agents.create_agent` — loop LLM↔tools com streaming, middleware e `checkpointer` nativos — em vez do harness completo `deepagents`.

**Rationale**:
- O problema exige um loop de tool-calling + RAG: o roteamento "dados vs. políticas" é **seleção de tool**, não orquestração multi-passo. `create_agent` entrega exatamente isso (assinatura verificada em langchain 1.4.x instalado: `model, tools, system_prompt, middleware, checkpointer`).
- Sem superfície de ataque a podar: filesystem virtual, subagentes (`task`) e `execute` (shell) **simplesmente não existem** no create_agent — elimina o trade-off de segurança que o deepagents exigiria gerenciar.
- Menos dependências e menos overhead de prompt: `deepagents` traz como deps diretas não usadas `langchain-anthropic`, `langchain-google-genai`, `langsmith` e built-ins (todos, filesystem, subagentes) que inflariam o system prompt sem benefício (a allowlist mínimo de filesystem ainda exige `read_file`).
- Precedente no portfólio do autor: AgendAI usa `create_agent` (ADR-026) com o mesmo sistema de middleware/checkpointer.

**Alternatives considered**:
- `deepagents.create_deep_agent` (harness completo, podado): blueprint oficial para tarefas multi-passo; rejeitado por evidência de oversizing — os built-ins (planejamento, filesystem virtual, subagentes, shell) não têm uso no atendimento de loja. Mantém-se como upgrade path se o agente crescer para pesquisa multi-passo/artefatos.
- `mda` (Managed Deep Agents): rejeitado por evidência — beta público; `mda deploy` exige LangSmith Cloud/BYOC (infra extra para o avaliador); `mda dev` é runtime de desenvolvimento.
- Loop ReAct manual em LangGraph: máximo controle, mais código próprio para manter; rejeitado (reinventar o harness).

---

## D2 — Runtime e "blueprint pronto": single container in-process + layout oficial LangGraph

**Decision**: Estruturar o projeto no **layout oficial do blueprint** (`langgraph.json` + módulo `agent/graph.py:graph`, igual ao template `deep-agent-python` e ao AgendAI), mas o **runtime em produção do desafio roda in-process dentro de UM container** (o próprio processo Python serve a UI Gradio e invoca o grafo compilado com `AsyncSqliteSaver`).

**Rationale (o trade-off central do projeto)**:

| Critério | A) In-process (Gradio + grafo) | B) LangGraph Server oficial |
|---|---|---|
| Serviços no Docker | **1 container** | 3-4 (server + Postgres + Redis [+ UI]) |
| Persistência | **SQLite** ✔ (pedido do autor) | Postgres apenas (server não suporta SQLite) |
| Chaves p/ avaliador | 1 (OpenAI) | 2 (OpenAI **+ LangSmith**, exigida até em self-host) |
| APIs prontas (threads/runs/SSE) | Não (não precisamos) | Sim |
| Setup do avaliador | `docker compose up` → abrir browser | `langgraph build` + `up`, mais peso |
| Upgrade path | `langgraph.json` já pronto → `langgraph build` funciona depois | nativo |

- O autor pediu explicitamente **agente mínimo** e **SQLite**; a opção B contradiz ambos e adiciona fricção ao avaliador (2ª chave, 3+ containers).
- Mantendo o `langgraph.json` fiel ao blueprint, `langgraph dev` funciona out-of-the-box (hot reload + LangSmith Studio para desenvolvimento) e `langgraph build` continua disponível como caminho documentado de escalação — **o blueprint é honrado no layout/DX sem pagar o custo operacional do server**.

**Alternatives considered**: LangGraph Server standalone (rejeitado acima); `langgraph dev` dentro do container como runtime final (rejeitado: persistência em diretório pickle `.langgraph_api`, não SQLite, e exige chave LangSmith do avaliador).

**Referências**: docs.langchain.com/langsmith/local-dev-testing; docs.langchain.com/langsmith/deploy-standalone-server; referência AgendAI (`docker-compose.yml` com server+pg+redis+nginx = o que estamos deliberadamente simplificando).

---

## D3 — Persistência: SQLite duplo papel

**Decision**:
1. **Conversas (checkpoints)**: `langgraph-checkpoint-sqlite` **AsyncSqliteSaver** (async p/ não bloquear a UI), arquivo `data/runtime/checkpoints.sqlite`, mapeado em volume Docker.
2. **Dados operacionais**: os 6 CSVs são carregados para um **SQLite relacional** (`data/runtime/store.sqlite`) no startup (ingestão idempotente); os tools fazem consultas SQL parametrizadas sobre ele.

**Rationale**: um único arquivo por finalidade, zero serviços extras, consultas determinísticas (preço/estoque/pedido — exatamente o que o SC-001 exige: 100% de fidelidade aos dados). Cumpre "SQLite para longo prazo" do autor.

**Alternatives considered**: pandas in-memory (perde persistência e dificulta joins pedidos↔cliente↔itens); Postgres (contradiz minimalismo; só entra se migrar para o LangGraph Server).

---

## D4 — RAG: ChromaDB local, guiado pelos 7 pontos de falha (Barnett et al., 2024)

**Decision**: RAG sobre `políticas_da_loja.pdf` com **ChromaDB persistente local** (`data/runtime/chroma/`), embeddings `text-embedding-3-small` (OpenAI, mesmo provedor), chunking **por seção do manual** (o PDF tem estrutura de capítulos numerados: horários, pagamento, trocas, frete, promoções, garantia) com metadados `{seção, título}`, top-k=3 com score mínimo.

**Mapeamento do artigo (Seven Failure Points — arXiv:2401.05856) → mitigações**:

| FP do artigo | Risco aqui | Mitigação no design |
|---|---|---|
| FP1 Missing Content | Pergunta sem resposta no manual (ex.: frete especial p/ bateria) | Score mínimo + regra de prompt: se retrieval fraco → declarar limite e orientar contato humano (FR-011) |
| FP2 Missed Top Ranked | Chunk certo fora do top-k | Chunking por seção (não por tamanho fixo) + k=3 + metadados de seção |
| FP3 Not in Context | Consolidação perde trecho | Chunks completos de seção (o manual é pequeno: ~3,5 mil palavras); sem sumarização prévia |
| FP4 Not Extracted | Resposta no chunk mas LLM não extrai | Tool retorna chunk bruto + instrução de citar a regra literalmente; testes de bateria (quickstart) |
| FP5 Wrong Format | Formato de resposta indevido | Contrato de resposta no system prompt (tom, preço original+desconto+final) |
| FP6 Incorrect Specificity | Regra com exceções (parcela mínima por faixa) | Chunking por seção preserva listas/condições completas; exemplos de ouro na bateria de teste |
| FP7 Incomplete | Resposta parcial (ex.: devolução sem citar prazo de reembolso) | Seções integrais + checklist de aceitação da spec vira casos de teste |

**Alternatives considered**: *prompt-stuffing* do PDF inteiro (~6-8k tokens/chamada — viável tecnicamente) — rejeitado por custo por mensagem e, sobretudo, porque o desafio avalia explicitamente a "arquitetura de retrieval" (README); embeddings locais (sentence-transformers) — rejeitados p/ manter imagem Docker leve e um único provedor.

---

## D5 — LLM: OpenAI (chave provisionada pela UI)

**Decision**: `ChatOpenAI` via `deepagents(model="openai:gpt-4o-mini")` como default, modelo configurável por env var (`OPENAI_MODEL`).

**Rationale**: function calling/tool calling maduro (núcleo do híbrido), custo baixo por mensagem, latência compatível com SC-007 (<30s). O autor gera uma chave dedicada para o avaliador; a UI Gradio tem tela de primeiro acesso que grava a chave em `.env` (FR-016).

**Alternatives considered**: Gemini free tier (menor custo p/ avaliador, mas decisão já tomada pelo autor); modelos locais Ollama (hardware do avaliador incerto, tool calling frágil).

---

## D6 — UI: Gradio (com onboarding da chave)

**Decision**: **Gradio** (`gr.ChatInterface`/`gr.Blocks`, `type="messages"`) no mesmo processo do agente: streaming token a token, exibição de tool calls via `metadata.title` (transparência = ponto de avaliação: "saber quando consultar dados vs. políticas"), e tela inicial de configuração coletando a chave OpenAI → grava `.env`.

**Alternatives considered**: **agent-chat-ui** (oficial LangChain, Next.js, mais profissional) — requer um LangGraph Server (contradiz D2) e adiciona stack Node/pnpm; fica documentada como upgrade path caso o projeto migre para o server oficial. Streamlit — sem streaming de tool calls tão limpo quanto Gradio.

---

## D7 — Pydantic: contratos de dados e configuração

**Decision**: Pydantic em 3 pontos: (1) schemas de entrada/saída dos tools (args tipados → menos alucinação de parâmetros); (2) validação de linhas CSV na ingestão (falhar cedo com erro claro); (3) `pydantic-settings` para `.env` (fonte única de configuração, lida também pela tela de onboarding).

---

## D8 — Docker: 1 container, dados como volume

**Decision**: `Dockerfile` único (`python:3.11-slim`), `docker-compose.yml` com **1 serviço** (conveniência), volumes nomeados/bind-mounts para `data/runtime/` (checkpoints, store, chroma) — estado sobrevive a rebuild. `.dockerignore` exclui `.env`, venvs e artefatos de spec.

**Alternatives considered**: stack multi-container estilo AgendAI (nginx+api+server+pg+redis+ui) — decisivamente rejeitada pelo autor.

**Nota (2026-11-04)**: o modo de execução via blueprint oficial (`langgraph build` + stack server/Postgres/Redis + agent-chat-ui) passa a ser opção documentada de escala — ver D9.

---

## D9 — Single agent vs. multi-agent e o modo de execução do blueprint

**Decision**: v1 com **um único agente** (`create_agent`) e tools agrupados por domínio. A arquitetura **multi-agente supervisor** fica documentada como caminho de evolução; o runtime do blueprint oficial (Agent Server) como modo de execução alternativo, também documentado.

**Por que single agent agora**: o desafio exige roteamento dados-vs-políticas, que um único LLM resolve via seleção de tools (visível na UI como blocos distintos). Multi-agente adicionaria um hop de LLM por turno (latência), tokens de orquestração e superfície de debug — sem ganho no escopo atual (constituição III: simplicidade radical).

**Design multi-agente documentado (se/quando escalar)**: padrão **supervisor** — um roteador coordena especialistas mapeados 1:1 às user stories:
- Atendimento/escopo (sem tools: persona, recusas, reclamações) — US4
- Catálogo (`search_products`, `get_product_details`) — US1
- Pedidos (`find_customer`, `list_customer_orders`) — US3
- Políticas (`search_policies`, `get_store_info`) — US2

Implementação: `langgraph-supervisor` (orquestrador central) ou `langgraph-swarm` (handoffs entre pares); estado compartilhado = histórico de mensagens + checkpointer por thread. **Quando pagaria**: prompts por domínio grandes e conflitantes; modelos distintos por domínio (modelo barato p/ chit-chat, forte p/ pedidos); domínios evoluindo em ritmos diferentes; novas capacidades transacionais com fluxos próprios (pós-venda, negociação).

**Modo de execução do blueprint (documentado)**: o mesmo `langgraph.json` serve a dois modos — (A) primário: processo único (UI + grafo + `AsyncSqliteSaver`), 1 container/1 chave, setup <15min; (B) escala: `langgraph build` + stack Agent Server/Postgres/Redis + `agent-chat-ui` (oficial) — stateless server, threads/runs/SSE, horizontal-ready. A factory `build_agent(checkpointer=...)` gera a variante adequada a cada modo.

**UI — decisão diferida (2026-11-04)**: acoplada (Gradio no processo, onboarding da chave FR-016, melhor UX p/ avaliador) vs. desacoplada (agent-chat-ui oficial sobre o Agent Server, zero código próprio). Recomendação: modo duplo A+B, decisão final na fase 7 — não bloqueia nada antes dela.

**Alternatives considered**: multi-agente v1 (rejeitado: custo sem benefício no escopo); MDA `mda` como blueprint (rejeitado: beta público + `deploy` exige cloud).

| Edge case (spec) | Mitigação |
|---|---|
| Pergunta vaga ("quero um presente") | System prompt: entender antes de consultar (perguntar faixa/instrumento) |
| Pergunta mista (preço + parcelamento) | Harness permite múltiplas tool calls por turno (dados + RAG) |
| Nome aproximado de produto ("Taylor 214") | Tool de busca com matching fuzzy (SQL `LIKE` + normalização) e confirmação antes de responder |
| Promoção inativa | Tool expõe apenas promoções `is_active=1` como vigentes; regra de não cumulatividade com PIX no prompt da tool |
| Identificação ambígua de cliente | Tool `get_customer` retorna candidatos; agente pede esclarecimento (nunca chuta) |
| Info fora das fontes (frete especial) | FP1: score mínimo + degradação honesta (FR-011) |
| Prompt injection via mensagem do cliente | Tools read-only; sem filesystem/shell expostos (D1); política PDF é dado confiável, input do cliente não é instrução |
| Chave inválida/ausente | Tela de onboarding valida com uma chamada barata antes de liberar o chat |

---

## Resolved NEEDS CLARIFICATION

Todos os técnicos foram resolvidos pelas diretrizes do autor + pesquisa acima; nenhum NEEDS CLARIFICATION permanece. Único ponto externo: prazo de entrega (está no e-mail do processo, fora do artefato) — não afeta o design.
