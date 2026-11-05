# ADRs — Architectural Decision Records

Decisões arquiteturais materiais do projeto, registradas na mesma entrega que as introduz
(constituicao, Principio V — Conhecimento Vivo).

## Indice

| ADR | Titulo | Status | Data |
|-----|--------|--------|------|
| [0001](./0001-runtime-single-container.md) | Runtime single container in-process em vez de LangGraph Server oficial | Aceito | 2026-11-04 |
| [0002](./0002-arquitetura-hibrida-tools-rag.md) | Arquitetura hibrida: function calling sobre SQLite + RAG ChromaDB | Aceito | 2026-11-04 |
| [0003](./0003-right-sizing-harness.md) | Right-sizing do harness: create_agent em vez de deepagents | Aceito | 2026-11-04 |

## Formato

```markdown
# ADR-NNNN: Titulo curto

## Status
Aceito | Proposto | Substituido por ADR-XXXX (data)

## Contexto
Forcas em jogo, restricoes, alternativas viaveis.

## Decisao
A escolha e o motivo.

## Consequencias
Positivas / Negativas / Neutras, incluindo trade-offs assumidos.
```

Fonte racional completa das decisoes: `specs/001-store-qa-agent/research.md` (D1-D8).
