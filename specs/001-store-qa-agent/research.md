# Research: Agente de Atendimento Virtual — Empório da Música

**Data**: 2026-11-03 | **Spec**: [spec.md](./spec.md) | **Referência de arquitetura**: projeto AgendAI (do autor), repositório local

Fonte de verdade do escopo: `Desafio Técnico AI Engineer 2026 2/desafio_tecnico_ai_eng_artefact.pdf`.

Diretrizes do autor (superior a qualquer default): **Python + Pydantic; deepagents da LangChain; LangGraph como runtime; blueprint pronto da LangChain; containers Docker; Gradio (ou UI pronta da LangChain se precisar escalar); SQLite para longo prazo; RAG com ChromaDB local guiado pelo artigo de falhas de RAG; agente MÍNIMO (sem constelação de serviços); ênfase em decisões técnicas documentadas, trade-offs e edge cases.**

---

## D1 — Harness do agente: `deepagents` (create_deep_agent)

**Decision**: Usar `deepagents.create_deep_agent` (LangChain) como harness do agente, com o conjunto de tools embutidos **podado** ao necessário.

**Rationale**:
- É o "batteries-included agent harness" oficial da LangChain sobre o runtime LangGraph (planejamento, subagentes via `task`, filesystem virtual, memória de longo prazo, middleware).
- Aderente ao pedido do autor e demonstra decisão arquitetural moderna ao avaliador: o loop LLM↔tools vem pronto e testado, nós entregamos a camada de domínio (tools, prompt, RAG, guardrails).
- Compatível com `checkpointer` (necessário para SQLite) e com `model="openai:..."`.

**Trade-off crítico (edge case de segurança)**: por default o deep agent expõe tools de filesystem (`write_file`, `edit_file`) e `execute` (shell). Para um agente de atendimento ao cliente isso é superfície de risco desnecessária (prompt injection via mensagem do cliente). **Mitigação**: configurar backend em memória/sem sandbox (sem `execute`) e limitar `permissions`/tools expostos; o agente final expõe apenas os 5-6 tools de domínio (read-only).

**Alternatives considered**:
- `langchain.create_agent` puro: mais leve, mas perde planejamento/subagentes e o alinhamento com o pedido do autor (e com o blueprint oficial `deep-agent-python`).
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

---

## Edge cases da spec → mitigações de design

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
