# Quickstart & Validação — Agente Empório da Música

Guia para rodar e validar o agente ponta a ponta (também serve de roteiro do avaliador — alinhado ao SC-006: < 15 min).

## Pré-requisitos

- Docker (compose v2) **ou** Python 3.11+ com `uv` para rodar local
- Chave da OpenAI (fornecida pelo autor do projeto por e-mail)

## Opção A — Docker (recomendada)

```bash
git clone <repo-público> && cd <repo>
docker compose up --build -d
# Abrir http://localhost:7860 → colar a chave na tela de configuração → Salvar e começar
```

## Opção B — Local

```bash
uv sync
cp .env.example .env   # ou cole a chave na tela da UI no primeiro acesso
uv run python -m app   # sobe Gradio em http://localhost:7860
```

No primeiro start, a ingestão acontece automaticamente: CSVs → `data/runtime/store.sqlite`; PDF de políticas → `data/runtime/chroma/`.

## Validação ponta a ponta (bateria de aceitação)

Roteiro de perguntas no chat — resultados esperados conforme [spec.md](./spec.md) e [contracts/tools.contract.md](./contracts/tools.contract.md):

| # | Pergunta | Resultado esperado |
|---|---|---|
| 1 | "Quais opções de violões disponíveis custando até R$1000?" | Lista somente violões reais com estoque > 0 e preço ≤ 1000 (ex.: Yamaha C40 R$ 599,90) — tool call de catálogo visível |
| 2 | "Quanto custa o Takamine GD20?" | R$ 2.199,00 e 5 unidades em estoque |
| 3 | "Qual o endereço da loja?" | Rua 14 de Maio, 3200 — Centro, Campo Grande-MS |
| 4 | "Me arrependi da minha compra, posso devolver meu pedido?" | Direito de arrependimento: 7 dias corridos, embalagem original, reembolso mesma forma de pagamento em até 10 dias úteis, frete por conta da loja — tool de políticas visível |
| 5 | "Sou Pedro Henrique Oliveira, cadê meu pedido?" | 2 pedidos: #3 delivered (rastreio BRDZ4561230BR) e #19 cancelled (pagamento não confirmado) |
| 6 | "Vocês vendem cordas avulsas?" | Redirecionamento educado (loja vende só instrumentos) |
| 7 | "Tem a promoção de Black Friday ainda?" | Informa que não está vigente e mostra preço atual (promoções BF estão `is_active=0`) |
| 8 | Pergunta mista: "Quanto custa o Taylor 214ce e dá pra parcelar em 12x?" | Preço + disponibilidade (tool de dados) **e** regra de parcelamento (tool de políticas) na mesma resposta |

## Critérios de sucesso verificáveis

- SC-001/002/003: as baterias acima respondidas sem valor inventado (conferir contra os CSVs/PDF).
- SC-005: ao capturar exemplos, gravar 3-5 conversas em `examples/` (.md), mantendo a #4 ou #8 como cenário não trivial.

## Testes automatizados

```bash
uv run pytest            # unitários: ingestão, tools (SQL determinístico), validação Pydantic
uv run pytest -m eval    # bateria de aceitação contra o agente real (requer chave; roda os cenários acima e asserita fatos-chave)
```

## Troubleshooting

| Sintoma | Causa provável | Ação |
|---|---|---|
| Tela pede chave toda hora | `.env` não persistido | verificar permissão de escrita no diretório / volume |
| Respostas de política genéricas | Chroma vazio | reiniciar container (reingestão) e checar logs de ingestão |
| "Weak retrieval" frequente | limiar alto demais | ajustar `RAG_MIN_SCORE` no `.env` |
