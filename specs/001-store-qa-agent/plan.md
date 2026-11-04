# Implementation Plan: Agente de Atendimento Virtual — Empório da Música

**Branch**: `001-store-qa-agent` | **Date**: 2026-11-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-store-qa-agent/spec.md`
**Research**: [research.md](./research.md) — decisões D1–D8 com trade-offs e alternativas

## Summary

Agente de atendimento ao cliente da Empório da Música (desafio Artefact AI Engineer): **deep agent** (`deepagents` da LangChain sobre runtime **LangGraph**) com arquitetura **híbrida** — function calling sobre dados operacionais (6 CSVs → SQLite) + **RAG** (ChromaDB) sobre o manual de políticas (PDF), guiado pelos 7 pontos de falha de RAG de Barnett et al. (2024). **Um único container Docker** servindo UI **Gradio** (com onboarding da chave OpenAI que grava `.env`), histórico de conversa via **SQLite checkpointer** (`AsyncSqliteSaver`). Layout do projeto segue o **blueprint oficial LangGraph** (`langgraph.json`, `langgraph new --template deep-agent-python`), mantendo `langgraph dev/build` como caminho de DX e upgrade — sem os serviços Postgres/Redis do server oficial, por decisão de minimalismo (ver D2).

## Technical Context

**Language/Version**: Python 3.11+ (exigido por `deepagents` e `langgraph-cli`)

**Primary Dependencies**: `deepagents` (harness), `langgraph` (runtime) + `langgraph-checkpoint-sqlite`, `langchain-openai` (modelo + embeddings), `pydantic` + `pydantic-settings`, `gradio` (UI), `chromadb` (vetores), `pypdf` (ingestão do manual)

**Storage**: SQLite `store.sqlite` (dados operacionais, read-only p/ agente), SQLite `checkpoints.sqlite` (threads/conversas via AsyncSqliteSaver), ChromaDB persistente local (políticas)

**Testing**: `pytest` (unit: ingestão/validação/tools SQL; eval: bateria de aceitação contra o agente real com LLM, marcada `eval`, requer chave)

**Target Platform**: container Docker (linux/amd64, `python:3.11-slim`) exposta em `:7860`; dev local macOS (`uv run`)

**Project Type**: single web-service (UI e agente no mesmo processo)

**Performance Goals**: resposta < 30s p95 por mensagem (SC-007); ingestão cold-start < 60s; setup do avaliador < 15 min (SC-006)

**Constraints**: tools read-only; sem filesystem/shell expostos ao LLM (podados do harness); chave OpenAI provisionada via UI (nunca commitada); 100% pt-BR; precisão factual obrigatória (SC-001/SC-002)

**Scale/Scope**: protótipo de avaliação: 1 conversa por vez × ~150 produtos, 20 pedidos, 50 clientes, 1 documento de políticas (~8 páginas)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

A constituição do projeto (`.specify/memory/constitution.md`) **não foi ratificada** (template com placeholders) — não há princípios formais a auditar. Gate funcional adotado neste plano, derivado da diretriz explícita do autor: **"agente mínimo — sem serviços desnecessários"**.

| Gate | Pré-Phase 0 | Pós-Phase 1 |
|---|---|---|
| Simplicidade: nº de serviços Docker justificado | ✅ (alvo: 1) | ✅ 1 serviço confirmado no design |
| Modularidade: UI desacoplável do agente via `langgraph.json` | ✅ | ✅ blueprint oficial mantido |
| Sem NFR inflado (HA, multiusuário, deploy cloud) | ✅ | ✅ fora de escopo (documentado em ui-flows.md) |

Sem violações a justificar (Complexity Tracking vazio de propósito).

## Project Structure

### Documentation (this feature)

```text
specs/001-store-qa-agent/
├── spec.md              # /speckit-specify
├── plan.md              # This file (/speckit-plan)
├── research.md          # Phase 0 — decisões D1–D8, trade-offs, edge cases
├── data-model.md        # Phase 1 — entidades, regras, visões
├── contracts/
│   ├── tools.contract.md    # Phase 1 — 5-6 tools read-only (schemas Pydantic)
│   └── ui-flows.md          # Phase 1 — onboarding da chave + chat
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks — ainda não criado)
```

### Source Code (repository root)

```text
pyproject.toml          # uv; deps pinadas com idade mínima
Dockerfile              # python:3.11-slim, um serviço
docker-compose.yml      # conveniência: 1 serviço + volumes
langgraph.json          # blueprint oficial: {"graphs": {"emporio_agent": "./agent/graph.py:graph"}}
.env.example
.gitignore              # inclui .env e data/runtime/

agent/
├── __init__.py
├── graph.py            # create_deep_agent(...) compilado com AsyncSqliteSaver (exporta `graph`)
├── prompt.py           # system prompt: persona, regras dados-vs-políticas, recusas, FR-005/006/007/011
└── tools/
    ├── catalog.py      # search_products, get_product_details
    ├── db.py           # conexão read-only ao store.sqlite (URI mode=ro), compartilhada pelos tools
    ├── orders.py       # find_customer, list_customer_orders
    └── policies.py     # search_policies (+ get_store_info)

app/
├── __main__.py         # entry point: python -m app
├── ui.py               # Gradio: chat + streaming + tool-call blocks + onboarding da chave
└── settings.py         # pydantic-settings (.env: OPENAI_API_KEY, OPENAI_MODEL, RAG_MIN_SCORE...)

ingestion/
├── load_csv.py         # CSV → store.sqlite com validação Pydantic
└── load_policies.py    # PDF → chunks por seção → Chroma (ids determinísticos)

data/
├── source/             # cópia versionada dos CSVs + PDF do desafio
└── runtime/            # gerado (gitignored): store.sqlite, checkpoints.sqlite, chroma/

tests/
├── unit/               # ingestão, tools (SQL), validação
└── eval/               # bateria de aceitação do quickstart (marcador `eval`)

examples/               # 3-5 conversas (.md) — entregável do desafio
README.md               # instruções + justificativas + limitações + uso de IA (FR-014)
```

**Structure Decision**: single project (opção 1) — um processo Python serve UI e agente. `agent/graph.py` permanece importável pelo `langgraph.json` para `langgraph dev` (DX com hot reload/Studio) e para upgrade futuro ao LangGraph Server. Contraste deliberado com o AgendAI (6 serviços): aqui 1.

## Complexity Tracking

Nenhuma violação de constituição/gate a justificar.
