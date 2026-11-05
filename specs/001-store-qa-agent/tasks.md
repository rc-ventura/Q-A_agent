---
description: "Task list for feature implementation — agente de atendimento Empório da Música"
---

# Tasks: Agente de Atendimento Virtual — Empório da Música

**Input**: Design documents from `/specs/001-store-qa-agent/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md, constitution v1.0.0

**Tests**: OBRIGATÓRIOS (constituição Princípio II — Test-First NON-NEGOTIABLE). Em cada fase, os testes são escritos ANTES da implementação e devem FALHAR primeiro (Red-Green-Refactor).

**Organization**: Tasks agrupadas por user story para implementação e teste independentes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizável (arquivos diferentes, sem dependências pendentes)
- **[Story]**: user story da spec (US1–US4); só nas fases de story
- Paths seguem a estrutura do plan.md (single project, sem `src/`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Inicialização do projeto, versionamento real (FR-013) e decisões arquiteturais registradas (constituição Princípio V)

- [x] T001 Initialize git repository at repo root; create `.gitignore` excluding `.env`, `data/runtime/`, `.venv/`, `__pycache__/`, `.DS_Store`; make initial commit (FR-013 exige histórico real de commits — começa aqui)
- [x] T002 [P] Create `pyproject.toml` via `uv init` with Python 3.11+ and pinned deps: `langchain` (emenda 2026-11-04: `deepagents` substituído por `langchain` após ADR-0003), `langgraph`, `langgraph-checkpoint-sqlite`, `langchain-openai`, `pydantic`, `pydantic-settings`, `gradio`, `chromadb`, `pypdf`; dev group: `pytest`, `ruff`; add `[tool.pytest.ini_options]` with marker `eval` (tests requiring OPENAI_API_KEY). ANTES de pinar, consultar no context7/documentação oficial as versões estáveis atuais de cada pacote e de suas APIs usadas no design (constituição Princípio I — Evidência ou Nada: proibido assumir versão/comportamento sem consultar a doc vigente)
- [x] T003 [P] Create `.env.example` with keys (sem valores reais): `OPENAI_API_KEY`, `OPENAI_MODEL`, `RAG_MIN_SCORE`
- [x] T004 [P] Copy the 6 CSVs and `políticas_da_loja.pdf` from `Desafio Técnico AI Engineer 2026 2/data/` into `data/source/` (fonte versionada)
- [x] T005 [P] Create `docs/adrs/README.md` and `docs/learning-lessons/README.md` com formato de índice (constituição Princípio V — Conhecimento Vivo)
- [x] T006 [P] Write `docs/adrs/0001-runtime-single-container.md` from research.md D2: in-process runtime + AsyncSqliteSaver vs LangGraph Server oficial (consequências: 1 chave para o avaliador, SQLite viável, upgrade path via `langgraph build`, trade-offs documentados)
- [x] T007 [P] Write `docs/adrs/0002-arquitetura-hibrida-tools-rag.md` from research.md D1+D4: deepagents com backend podado + function calling sobre SQLite + RAG ChromaDB com mitigações FP1–FP7
- [x] T008 Commit setup phase (commits pequenos e reais — FR-013)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Config, banco SQLite + ingestão com validação, RAG store, grafo base e prompt base — bloqueiam TODAS as stories

**CRITICAL**: Nenhuma user story pode começar antes desta fase completar

### Tests first (TDD — devem falhar antes da implementação)

- [x] T009 [P] Write failing unit test `tests/unit/test_settings.py`: `Settings` carrega de `.env`; `openai_api_key` ausente → `is_configured()` retorna False; defaults: `openai_model == "gpt-4o-mini"`, `rag_min_score == 0.25`; paths `data/runtime/`
- [x] T010 [P] Write failing unit test `tests/unit/test_schema.py`: schema cria 6 tabelas + view `v_active_promotions`; CHECK constraints rejeitam violações citadas verbatim do data-model.md: `products.price_brl >= 0`, `products.stock_quantity >= 0`, `products.status IN ('active','inactive')`, `orders.status IN ('pending','confirmed','shipped','delivered','cancelled')`, `orders.total_brl >= 0`, `orders.tracking_code` NOT NULL apenas quando `status='shipped'`, `order_items.quantity > 0` com PK composta `(order_id, product_id)`, `promotions.discount_percent` com `0 < x <= 100`, `promotions.is_active IN (0,1)`
- [x] T011 [P] Write failing unit test `tests/unit/test_load_csv.py`: ingestão idempotente (rodar 2x não duplica); linha inválida → erro de startup com mensagem contendo arquivo + linha + campo (data-model.md: "falhar cedo"); contagens no banco == linhas dos CSVs em `data/source/`
- [x] T012 [P] Write failing unit test `tests/unit/test_load_policies.py`: PDF → chunks por seção do manual; metadados por chunk `{section_no, section_title, page}`; IDs determinísticos `policy_<seção>_<n>`; reingestão não duplica (idempotente)
- [ ] T013 [P] Write failing unit test `tests/unit/test_graph.py`: grafo compila; checkpointer é `AsyncSqliteSaver` apontando para `data/runtime/checkpoints.sqlite`; o **dispatcher** expõe apenas as 4 tools-roteadoras para especialistas (filesystem/shell inexistentes no `create_agent` — research.md D1/ADR-0003/0004); modelo vem de settings

### Implementation (na ordem; cada uma depende do seu teste falhar)

- [x] T014 Implement `app/settings.py` com pydantic-settings: campos do T009 + `store_db_path`, `checkpoint_db_path`, `chroma_dir`, `data_source_dir`; método `is_configured()`; helper `save_api_key(key)` que grava `.env` e recarrega (base para F0/FR-016) — passar T009
- [x] T015 Implement `ingestion/schema.py`: `create_schema(conn)` criando as 6 tabelas com as constraints verbatim do T010 (data-model.md) + view `v_active_promotions` (products ⋈ promotions `WHERE is_active=1`, com coluna `final_price_brl = round(price_brl * (1 - discount_percent/100), 2)`) — passar T010
- [x] T016 Implement `ingestion/load_csv.py`: lê os 6 CSVs de `data/source/`, valida cada linha com models Pydantic conforme regras do data-model.md (ex.: `email` contém `@`, FKs existem), insere em `data/runtime/store.sqlite` de forma transacional e idempotente; erro de validação aborta startup com arquivo+linha+campo — passar T011
- [x] T017 Implement `agent/tools/db.py`: helper `open_readonly()` que abre `store.sqlite` com URI `mode=ro` (regra transversal dos contratos: tools nunca escrevem) — usado por todos os tools de dados
- [x] T018 Implement `ingestion/load_policies.py`: extrai `políticas_da_loja.pdf` com pypdf, divide por seções numeradas do manual, grava na collection Chroma persistente em `data/runtime/chroma/` com embeddings OpenAI `text-embedding-3-small`, IDs determinísticos e metadados do T012 — passar T012
- [ ] T019 Write failing unit test `tests/unit/test_prompt.py`: prompt contém marcadores das regras — persona Empório da Música (tom informal-profissional), proibição de inventar preço/estoque (FR-002), políticas somente do manual (FR-003), recusa de fora de escopo (FR-009), proibição de ações transacionais (FR-012), formato promoção (preço original + % + final, FR-006)
- [ ] T020 Implement `agent/prompt.py`: system prompt base com persona, roteamento dados-vs-políticas (FR-004), formato de resposta e guardrails do T019 — passar T019
- [x] T021 Implement `agent/graph.py` — dispatcher: `create_agent(model` de settings, `tools=[4 tools-roteadoras para especialistas — placeholder até as stories]`, `system_prompt` de prompt.py, `checkpointer=AsyncSqliteSaver(checkpoint_db_path)`) exportando `graph`; factory monta especialistas `agent/specialists/*.py` conforme stories chegam (catalog em T026, policies em T029, orders em T033, service em T037 — ADR-0004) — passar T013
- [x] T022 Create `langgraph.json` na raiz: `{"dependencies": ["."], "graphs": {"emporio_agent": "./agent/graph.py:graph"}, "env": ".env"}` (blueprint oficial — research.md D2; habilita `langgraph dev` para DX)
- [ ] T023 Smoke test manual: `uv run pytest` verde (sem marker `eval`) + commit da fase

**Checkpoint**: Foundation pronta — stories podem começar (US1 ∥ US2 se houver paralelismo)

---

## Phase 3: User Story 1 - Consulta de catálogo, preço e disponibilidade (Priority: P1) MVP

**Goal**: Agente responde preço/estoque/disponibilidade/promoções exclusivamente a partir dos dados (FR-002), com promoção ativa exibindo original + % + final (FR-006) e fora de estoque sugerindo alternativas (FR-007)

**Independent Test**: Pergunta "Quais opções de violões disponíveis custando até R$1000?" via tool retorna somente violões reais, preço ≤ 1000, estoque > 0 — sem inventar nada (spec US1)

### Tests first (TDD)

- [ ] T024 [US1] Write failing unit test `tests/unit/test_tools_catalog.py` cobrindo o contrato `contracts/tools.contract.md` §1–2 verbatim: `search_products(query, category, max_price_brl=None, in_stock_only=True, limit=5)` — fuzzy com normalização de acentos ("violao" casa "Violões"); "violões até 1000" inclui Yamaha C40 R$ 599,90; produto em promoção ativa traz `active_promotion {discount_percent, final_price_brl}` somente se `is_active=1` (produto 127, 10%); `get_product_details("Takamine GD20")` → preço 2199.0 e estoque 5; produto inexistente → `{"error": "not_found", "did_you_mean": [...]}`; Giannini GF-3D aparece com estoque 0 quando `in_stock_only=False`

### Implementation

- [ ] T025 [US1] Implement `agent/tools/catalog.py`: `search_products` + `get_product_details` com args validados por Pydantic, SQL read-only via `agent/tools/db.py`, join com `v_active_promotions`, docstrings completas (constituição VI — é o contrato que o LLM lê) — passar T024
- [ ] T026 [US1] Registrar os tools de catálogo em `agent/graph.py` e estender `agent/prompt.py` com regras específicas de catálogo: sempre exibir original+%+final quando promoção ativa; promoção vencida → transparência + preço atual (US1 cenário 4); sem estoque → alternativas em estoque (FR-007)
- [ ] T027 [US1] Commit US1

**Checkpoint**: US1 testável isoladamente via tools (unit) — SC-001 aferível no nível dos tools

---

## Phase 4: User Story 2 - Políticas e informações institucionais da loja (Priority: P1)

**Goal**: Agente responde horários/endereço/pagamento/trocas/frete/garantia fiel ao manual (FR-003), citando a regra; retrieval fraco → declara limite e orienta contato humano (FR-011)

**Independent Test**: "Me arrependi da minha compra, posso devolver meu pedido?" → resposta contém 7 dias corridos, embalagem original, reembolso em até 10 dias úteis, frete por conta da loja (spec US2)

### Tests first (TDD)

- [ ] T028 [P] [US2] Write failing unit test `tests/unit/test_tools_policies.py` cobrindo `contracts/tools.contract.md` §3 e §6 verbatim: `search_policies(question, top_k=3)` — pergunta "devolução por arrependimento" retorna chunk da seção 4 contendo "7 (sete) dias" e "10 dias úteis", com `section_title` presente; chunks abaixo de `similarity >= 0.25` (limiar configurável via settings) excluídos; nenhum chunk acima do limiar → `{"retrieval": "weak"}`; texto retornado é bruto (sem sumarização — FP3/FP4); `get_store_info()` sem args retorna bloco fixo com endereço (Rua 14 de Maio, 3200 — Centro, Campo Grande-MS), WhatsApp (67) 3341-4444 e horários (Seg–Sex 09:00–18:00, Sáb 09:00–13:00)

### Implementation

- [ ] T029 [US2] Implement `agent/tools/policies.py`: `search_policies` (query na collection Chroma, top_k=3, filtro por `settings.rag_min_score`, retorna `{section_title, text, similarity}`) + `get_store_info` (bloco fixo) — passar T028
- [ ] T030 [US2] Registrar tools de políticas em `agent/graph.py` e estender `agent/prompt.py`: citar a regra literalmente; retrieval `weak` → seguir FR-011 (declarar limite + canais de contato humano); respostas de política nunca "de cabeça"
- [ ] T031 [US2] Commit US2

**Checkpoint**: US1 + US2 funcionam independentemente — SC-002 aferível no nível do tool

---

## Phase 5: User Story 3 - Acompanhamento de pedido (Priority: P2)

**Goal**: Agente identifica o cliente por nome completo ou e-mail antes de expor pedidos (FR-005), informa status/previsão/rastreio e explica cancelamentos com transparência; ambíguo/inexistente → pede esclarecimento, nunca chuta nem vaza dados além do mínimo

**Independent Test**: "Sou Pedro Henrique Oliveira, cadê meu pedido?" → retorna pedido #3 (delivered, rastreio BRDZ4561230BR) e #19 (cancelled + motivo "Pagamento não confirmado dentro do prazo") (spec US3)

### Tests first (TDD)

- [ ] T032 [US3] Write failing unit test `tests/unit/test_tools_orders.py` cobrindo `contracts/tools.contract.md` §4–5 verbatim: `find_customer(name=None, email=None)` (ao menos um obrigatório) — busca por nome case/acento-insensível; retorna `{matches: [{customer_id, name, city}]}` SEM e-mail/telefone (minimização LGPD); 0 matches → `{"matches": []}`; nome ambíguo → múltiplos candidatos; `list_customer_orders(customer_id)` — cliente 3 retorna orders #3 delivered (tracking_code BRDZ4561230BR, estimated_delivery presente) e #19 cancelled com `notes`; `tracking_code` aparece somente quando presente; pedido cancelado sempre acompanhado de `notes` quando houver; inclui itens (nomes de produtos)

### Implementation

- [ ] T033 [US3] Implement `agent/tools/orders.py`: `find_customer` + `list_customer_orders` com Pydantic args e SQL read-only via `agent/tools/db.py`, docstrings completas — passar T032
- [ ] T034 [US3] Registrar tools de pedidos em `agent/graph.py` e estender `agent/prompt.py`: FR-005 verbatim (identificar antes de expor; ambíguo → esclarecimento); múltiplos pedidos apresentados com clareza; cancelamento sempre explica o motivo das `notes`
- [ ] T035 [US3] Commit US3

**Checkpoint**: US1 + US2 + US3 funcionam independentemente

---

## Phase 6: User Story 4 - Persona, escopo e situações especiais (Priority: P3)

**Goal**: Persona consistente da loja; acessórios redirecionados (FR-008); fora de escopo recusado com cordialidade (FR-009); reclamações acolhidas com orientação de retorno em 24h úteis (fluxo do manual §7.3); edge cases da spec (vago, misto, fuzzy, info inexistente, negociação) cobertos por prompt + testes

**Independent Test**: "Vocês vendem cordas avulsas pro meu violão?" → explica exclusividade de instrumentos + redireciona; "Qual a capital do Canadá?" → recusa cordial (spec US4)

### Tests first (TDD)

- [ ] T036 [US4] Write failing eval test `tests/eval/test_scope_and_persona.py` (marker `eval`, requer OPENAI_API_KEY, skip sem chave): acessório (cordas/palhetas) → redirecionamento com menção a "instrumentos"; fora de escopo (capital do Canadá) → recusa cordial sem responder o conteúdo; reclamação → empatia + prazo "24 horas úteis"; pergunta vaga ("quero um presente") → agente faz pergunta de esclarecimento em vez de chutar; cliente negociando desconto → sem condições inexistentes, menciona formas de pagamento reais; tentativa de ação transacional ("cancela meu pedido", "faz o pedido pra mim") → recusa + encaminhamento ao atendimento humano (FR-012)

### Implementation

- [ ] T037 [US4] Estender `agent/prompt.py` com as regras de escopo/persona verbatim dos FRs: FR-008 (só instrumentos, redirecionar acessórios), FR-009 (recusa cordial de fora de escopo), fluxo de reclamação (empatia + registrar + 24h úteis), FR-012 (sem ações transacionais — informa e encaminha), PIX 5% não cumulativo com promoção (FR-006 final), negociação de desconto recusada, pergunta vaga → entender antes de consultar; iterar até T036 verde
- [ ] T038 [US4] Commit US4

**Checkpoint**: Todas as stories funcionam independentemente

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: UI completa, empacotamento, entregáveis do desafio e validação final

- [ ] T039 Implement `app/ui.py` fluxo F1 (contracts/ui-flows.md): `gr.ChatInterface`/`gr.Blocks` com `type="messages"`, streaming token a token, tool calls como blocos recolhíveis com título "Consultando catálogo/políticas/pedidos…" via metadata, botão "Nova conversa" → novo `thread_id` (uuid4; checkpoint anterior permanece no SQLite), erros de runtime (provider fora, rate limit) → mensagem amigável pt-BR com orientação
- [ ] T040 Implement `app/ui.py` fluxo F0 (FR-016) + `app/__main__.py` (entry point `python -m app` do quickstart): detecta chave ausente/inválida (chamada mínima barata à API), tela com campo password + "Salvar e começar" → `save_api_key()` grava `.env` local, valida, roda ingestão (T016+T018) e libera o chat; falha → erro claro, permanece na tela; chave nunca em logs nem em mensagens
- [ ] T041 [P] Create `Dockerfile` (python:3.11-slim, uv sync, EXPOSE 7860, CMD do app) e `docker-compose.yml` (1 serviço, volume nomeado/bind-mount para `data/runtime/`, porta 7860) e `.dockerignore` (`.env`, `.venv/`, `specs/`, `data/runtime/`, venvs) conforme research.md D8
- [ ] T042 [P] Write eval battery `tests/eval/test_quickstart_battery.py` (marker `eval`, requer chave, skip sem ela): ≥10 perguntas de catálogo e ≥10 de políticas (SC-001/SC-002 exigem ≥10 por categoria), englobando as 8 perguntas-ouro do quickstart.md com assertivas de fatos-chave (Yamaha C40 599,90; Takamine GD20 2199 + estoque 5; endereço exato; arrependimento 4 fatos; Pedro Henrique → 2 pedidos com motivo; cordas → redirecionamento; Black Friday inativa → preço atual; mista Taylor 214ce + 12x); cenário multi-turno de 2 turnos com referência anafórica (FR-010, ex.: "quanto custa o Yamaha FG800?" → "e o mais barato de nylon?"); asserções não-funcionais: cada resposta ≤ 30s (SC-007) e cenários primários resolvidos em ≤ 2 trocas (SC-004)
- [ ] T043 Write `README.md` na raiz (FR-014 verbatim): instruções completas (Docker `compose up` + local `uv sync` + `uv run python -m app`), provedor do modelo, chave via tela de onboarding; justificativa das decisões técnicas (framework, LLM, arquitetura de retrieval, estratégia de prompt — referenciando ADRs 0001/0002 e research.md); limitações conhecidas (retenção ilimitada dos checkpoints, autenticação leve do cliente, single-user, sem WhatsApp real) + "o que faria com mais tempo"; declaração de uso de assistentes de IA no workflow (Devin/Spec-Driven Development com speckit) e como foram usados
- [ ] T044 Create 3–5 example conversations em `examples/*.md` (FR-015/SC-005): cenários variados das 4 stories, incluindo ≥1 não trivial (devolução com regra do manual OU pergunta mista #8 do quickstart)
- [ ] T045 Remove o bloco "SYNC IMPACT REPORT" do topo de `.specify/memory/constitution.md` (regra de Governance: material temporário, remover antes do commit) e commit
- [ ] T046 Final validation: `uv run pytest` verde; `uv run pytest -m eval` verde com chave; percorrer o checklist do quickstart.md end-to-end cronometrado (<15 min do clone à primeira conversa — SC-006) a partir do Docker; registrar achados relevantes em `docs/learning-lessons/` (constituição V)
- [ ] T047 Create public GitHub repo do projeto e push final com histórico acumulado (FR-013) — REQUER aprovação explícita do usuário antes de executar (push é efeito externo); nunca commitar `.env`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — começa imediatamente
- **Foundational (Phase 2)**: depende de Setup — BLOQUEIA todas as stories
- **User Stories (Phases 3–6)**: dependem de Foundational
  - US1 e US2 são ambas P1 e independentes (tools em arquivos diferentes) → podem paralelizar
  - Recomendado em execução solo: US1 → US2 → US3 → US4 (ordem de prioridade)
- **Polish (Phase 7)**: depende das stories desejadas completas (T039/T040 requerem `agent/graph.py` com tools registrados; T042/T044 requerem agente funcional)

### Within Each Story (TDD)

- Teste escrito primeiro, deve FALHAR pelo motivo certo
- Implementação mínima até verde; refactor com verde mantido
- Commit por story (FR-013: histórico real)

### Parallel Opportunities

- Setup: T002–T007 em paralelo (arquivos diferentes)
- Foundational tests: T009–T013 em paralelo (arquivos diferentes, sem deps)
- Cross-story: T028 (US2 test) pode rodar junto com T025 (US1 impl) — arquivos diferentes
- Polish: T041, T042 em paralelo

## Parallel Example: User Story 1 + foundational tests

```bash
# Foundational tests (fase 2) em paralelo:
Task: "Write failing unit test tests/unit/test_settings.py"
Task: "Write failing unit test tests/unit/test_schema.py"
Task: "Write failing unit test tests/unit/test_load_csv.py"
Task: "Write failing unit test tests/unit/test_load_policies.py"
Task: "Write failing unit test tests/unit/test_graph.py"

# Cross-story (após Foundational):
Task: "[US1] Implement agent/tools/catalog.py"          # arquivo A
Task: "[US2] Write failing unit test tests/unit/test_tools_policies.py"  # arquivo B
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup → Phase 2: Foundational (CRÍTICO — bloqueia tudo)
2. Phase 3: US1 (catálogo)
3. STOP e VALIDATE: `pytest -k catalog` verde; resposta a "violões até R$1000" via script manual sem chave real não se aplica — validar tools em nível unitário; com chave, primeiro chat funcional
4. Demo/MVP: agente respondendo catálogo com precisão (coração do SC-001)

### Incremental Delivery

1. Setup + Foundational → fundação pronta
2. +US1 → testa isolado → demo (MVP)
3. +US2 → testa isolado → demo (políticas)
4. +US3 → testa isolado → demo (pedidos)
5. +US4 → testa isolado → demo (persona/escopo)
6. Polish → entregáveis do desafio (README, examples, Docker, repo público)

---

## Notes

- [P] = arquivos diferentes, sem dependências pendentes
- [US#] mapeia para a user story da spec (rastreabilidade)
- TDD constitucional: todo teste falha antes; código sem teste prévio não é mergeável
- Segredos: `.env` nunca commitado (verificado em T047); chave do avaliador circula por e-mail
- Constitution v1.0.0 governa: simplicidade (Princípio III), ADR para decisões (V), sem ruído (VI), clarificar antes (VII)
