# LL-0001: RAG — distancia L2^2 nao e cosseno; o titulo da secao precisa entrar no embedding

Data: 2026-11-04. Contexto: US2 (policies specialist). Referencias: ADR-0002 (FP1/FP2), agent/policies_rag.py.

## O que aconteceu

Dois bugs de qualidade de retrieval, ambos so descobertos porque o teste
consultava a collection de verdade:

1. **Threshold na escala errada.** Chroma devolve distancia L2^2
   (hnsw:space="l2" default). Usar `score = 1 - dist` com
   `min_score=0.25` fazia TODAS as queries relevantes virar "weak"
   (relevantes medidos: 0.67–1.17; nonsense: ~1.95). Com embeddings
   normalizados (MiniLM ONNX default do Chroma), a conversao correta e
   `cosseno = 1 - d^2/2` — arrependimento passa a 0.43, nonsense a -0.91.

2. **Secao certa fora do top-3 (FP2 real).** Para "horario de
   funcionamento", a secao 2 perdia para secoes 8.3/6.1/4.2 porque o
   conteudo dela e quase so tabela — o titulo nao entrava no embedding.
   Fix: documentar o chunk como `Secao N — Titulo\n\n<texto>` no index
   (metadados mantidos separados para citacao). Secao 2 subiu para o
   rank 1 (0.523).

## Regra derivada

- Nunca assuma a metrica/escala do vetor-store: meca distancias reais de
  queries boas vs. nonsense antes de fixar o threshold (constituicao:
  evidencia ou nada).
- Embedar o "contexto de posicao" (titulo de secao/capitulo) junto do
  chunk e a mitigacao mais barata de FP2 para corpus estruturado —
  melhor que aumentar top-k ou adicionar re-ranker num corpus pequeno.

## Como detectar mais cedo

Bateria de teste com query real por secao alvo (nao so "retorna lista"),
incluindo secoes-tablela — o teste de "horario" pega os dois bugs.
