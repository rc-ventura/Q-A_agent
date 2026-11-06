# Contract: Tools do agente (function calling)

Interface entre o LLM e as fontes de dados. Todos os tools são **read-only**. Schemas de argumentos definidos com Pydantic.

## 1. `search_products`
Catálogo: busca por texto/faixa de preço/categoria/disponibilidade.

**Args**: `query: str | None`, `category: str | None`, `max_price_brl: float | None = None`, `in_stock_only: bool = True`, `limit: int = 5`
**Retorna**: lista de até `limit` produtos `{name, price_brl, stock_quantity, category, description, active_promotion?: {discount_percent, final_price_brl, campaign}}`.
**Garantias**: matching fuzzy em nome (LIKE + normalização de acentos); promoção incluída somente se `is_active=1`, sempre com `price_brl` original + `%` + final.
**Erros**: nenhum match → lista vazia (o agente formula "não encontrei" + alternativas; nunca inventa).

## 2. `get_product_details`
Detalhes de um produto específico (specs completas).

**Args**: `product_name: str` (fuzzy) **ou** `product_id: int`
**Retorna**: `{name, price_brl, stock_quantity, status, category, description, specs(dict), active_promotion?}` (`status`: `active`, `discontinued` ou `coming_soon`; inclui produtos fora do catálogo ativo).
**Erros**: produto não encontrado → `{"error": "not_found", "did_you_mean": [...]} ` (o agente confirma com o cliente antes de responder).

## 3. `search_policies`
RAG sobre o manual de políticas (ChromaDB).

**Args**: `question: str`, `top_k: int = 3`
**Retorna**: lista `{section_title, text, similarity}` — somente chunks com `similarity >= limiar` (default 0.25; configurável).
**Garantias**: texto bruto da seção, sem sumarização (FP3/FP4 do artigo de referência).
**Erros**: nenhum chunk acima do limiar → `{"retrieval": "weak"}` → agente declara limite e orienta contato humano (FR-011); nunca responde política "de cabeça".

## 4. `find_customer`
Identificação do cliente (passo 1 do atendimento de pedidos).

**Args**: `name: str | None`, `email: str | None` (ao menos um obrigatório)
**Retorna**: `{matches: [{customer_id, name, city}]}` (sem e-mail/telefone completos — minimização LGPD).
**Erros**: 0 matches → `{"matches": []}`; >1 match → o agente MUST pedir esclarecimento (ex.: cidade ou e-mail) antes de prosseguir.

## 5. `list_customer_orders`
Pedidos de um cliente identificado.

**Args**: `customer_id: int`
**Retorna**: pedidos `{order_id, order_date, status, total_brl, payment_method, tracking_code?, estimated_delivery?, notes?}` + itens (`items: [{name, quantity}]`). `status` e `payment_method` vêm em português para o cliente (`aguardando pagamento`, `confirmado`, `enviado`, `entregue`, `cancelado`; `PIX`, `boleto`, `cartão de débito`, `cartão de crédito em Nx`).
**Garantias**: tracking exibido só quando presente; pedido `cancelled` sempre acompanhado de `notes` quando houver.

## 6. (Opcional P3) `get_store_info`
Atalho determinístico para dados institucionais estáveis (endereço, telefone, horário) — evita round de retrieval para fatos fixos.

**Args**: nenhum. **Retorna**: bloco fixo (endereço, WhatsApp, horários).

## Regras transversais

- Nenhum tool escreve nas fontes (sem INSERT/UPDATE/DELETE; WAL read-only na conexão).
- Argumentos validados por Pydantic; arg inválido retorna erro tipado que o agente traduz em pergunta de esclarecimento.
- Todo resultado cru entra no trace (LangSmith tracing opcional via env) — auditável no pós-avaliação.
