# Data Model: Agente de Atendimento Virtual — Empório da Música

**Data**: 2026-11-03 | **Fonte**: CSVs em `Desafio Técnico AI Engineer 2026 2/data/` + spec.md

Dois domínios de dados: **operacional** (da loja, read-only para o agente) e **conversacional** (estado do agente, gerenciado pelo checkpointer).

## Domínio operacional (SQLite `store.sqlite`, ingerido dos CSVs no startup)

### `categories`
| Campo | Tipo | Regras |
|---|---|---|
| category_id | INTEGER PK | > 0 |
| name | TEXT NOT NULL | único |
| description | TEXT | — |

### `products`
| Campo | Tipo | Regras |
|---|---|---|
| product_id | INTEGER PK | > 0 |
| name | TEXT NOT NULL | — |
| category_id | INTEGER FK → categories | deve existir |
| price_brl | REAL NOT NULL | >= 0 |
| description | TEXT | — |
| stock_quantity | INTEGER NOT NULL | >= 0 |
| status | TEXT NOT NULL | `active`/`inactive` |
| specs | TEXT (JSON) | blob opaco; exposto ao agente como JSON string |
| created_at | TEXT (ISO date) | — |

### `customers`
| Campo | Tipo | Regras |
|---|---|---|
| customer_id | INTEGER PK | > 0 |
| name | TEXT NOT NULL | — |
| phone | TEXT | formato `(67) 9XXXX-XXXX` (informativo, não-obrigatório na validação) |
| email | TEXT | contém `@` (validação leve) |
| city | TEXT | — |

### `orders`
| Campo | Tipo | Regras |
|---|---|---|
| order_id | INTEGER PK | > 0 |
| customer_id | INTEGER FK → customers | deve existir |
| order_date | TEXT (ISO date) | — |
| status | TEXT NOT NULL | enum: `pending`, `confirmed`, `shipped`, `delivered`, `cancelled` |
| total_brl | REAL NOT NULL | >= 0 |
| payment_method | TEXT | `pix`, `debit`, `boleto`, `credit_3x`, `credit_6x`, `credit_12x` |
| tracking_code | TEXT NULL | obrigatório apenas se `status = 'shipped'` |
| estimated_delivery | TEXT (ISO date) NULL | — |
| notes | TEXT NULL | motivo (ex.: cancelamento) |

**Transições de estado** (informativas para as respostas): `pending → confirmed → shipped → delivered`; `pending → cancelled`.

### `order_items`
| Campo | Tipo | Regras |
|---|---|---|
| order_id | INTEGER FK → orders | PK composta com product_id |
| product_id | INTEGER FK → products | — |
| quantity | INTEGER NOT NULL | > 0 |

### `promotions`
| Campo | Tipo | Regras |
|---|---|---|
| promotion_id | INTEGER PK | > 0 |
| product_id | INTEGER FK → products | deve existir |
| discount_percent | REAL NOT NULL | 0 < x <= 100 |
| description | TEXT | nome da campanha |
| is_active | INTEGER (0/1) NOT NULL | **somente 1 é apresentável ao cliente** |

### Visões derivadas usadas pelos tools
- `v_active_promotions` = products ⋈ promotions(is_active=1): nome, preço original, desconto %, preço final calculado.
- Consulta de pedidos por cliente: customers ⋈ orders (⋈ order_items quando perguntado o conteúdo).

### Entidade documental (fora do SQL)
- **`policies` (ChromaDB)**: chunks do PDF de políticas. Metadados por chunk: `section_no` (ex.: "4"), `section_title` (ex.: "Política de Trocas e Devoluções"), `page`. IDs determinísticos (`policy_<seção>_<n>`) regravam na reingestão (idempotente).

## Domínio conversacional (SQLite `checkpoints.sqlite`, gerenciado pelo LangGraph)

Não modelamos tabelas manualmente: o `AsyncSqliteSaver` persiste por `thread_id` o estado do grafo (mensagens, resultados de tools, writes pendentes). Um `thread_id` = uma conversa da UI. Retenção: ilimitada no protótipo (documentado como limitação; TTL/limpeza entra no "com mais tempo").

## Validação (Pydantic) na ingestão

Cada linha CSV é validada por um model Pydantic antes do insert. Linha inválida → erro de startup com mensagem clara (qual arquivo, qual linha, qual campo) — falhar cedo em vez de servir dado corrompido ao cliente.

## Mapeamento FR → dados

- FR-002 (preço/estoque fiéis) → leitura direta em `products`/`v_active_promotions` no momento da pergunta.
- FR-005 (pedido por cliente) → `customers` por nome (case/acento-insensível) ou e-mail; ambiguidade → lista de candidatos, sem vazar dados.
- FR-006 (promoções) → somente `is_active=1`; preço final = `price_brl * (1 - discount/100)`, arredondado a 2 casas.
