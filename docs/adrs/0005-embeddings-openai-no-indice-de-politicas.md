# ADR-0005: Embeddings OpenAI (text-embedding-3-small) no índice de políticas

## Status
Aceito (2026-11-05). Substitui a escolha implícita do MiniLM padrão do Chroma, que divergia do T018 do `tasks.md`.

## Contexto
O índice de políticas (ADR-0002) foi construído com a função de embedding padrão do Chroma, o
MiniLM-L6 em ONNX, um modelo treinado em inglês. A bateria de eval do quickstart (T042) mostrou
respostas do tipo "não tenho essa informação" para perguntas cobertas pelo manual. Medição direta
nas 12 perguntas de política da bateria, verificando em que posição aparece a seção correta:

| Embedding | Seção correta no top-3 | Casos piores |
|---|---|---|
| MiniLM padrão do Chroma | 8 de 12 | "parcelar": posição 11; "endereço": 11; "PIX": 13 |
| `text-embedding-3-small` | 12 de 12 | todos na posição 1 a 3 |

Alternativas consideradas: manter o MiniLM e aumentar o `top_k` (mascara o problema, polui o
contexto do especialista e não resolve "endereço" e "PIX"); modelo multilíngue local
(`paraphrase-multilingual`, exige dependência pesada e imagem maior); re-ranker (complexidade
desproporcional para um manual de ~35 trechos).

## Decisão
Usar `text-embedding-3-small` via `OpenAIEmbeddingFunction` do Chroma, com a chave lida da variável
`OPENAI_API_KEY` no momento do uso (o Chroma grava apenas o nome da variável, nunca o segredo).
O índice passa a usar espaço cosseno (`score = 1 - distância`) e é reconstruído a cada
inicialização, pois é derivado do PDF: isso evita conflito entre índices gravados com embedding ou
métrica diferentes. O limiar `RAG_MIN_SCORE` sobe de 0,25 para 0,30: perguntas sem relação com o
manual pontuam até 0,26 e o pior caso relevante pontua 0,40.

## Consequências
- Positivas: recuperação correta em 12/12 perguntas medidas; a imagem Docker não precisa mais do
  modelo ONNX; alinha o código ao T018; sem dependência nova (o pacote `openai` já era usado).
- Negativas: a indexação passa a exigir chave e rede (uma chamada com ~35 trechos a cada start,
  fração de centavo); consultas ganham uma chamada de embedding (~100 ms).
- Neutras: os testes unitários injetam a função local do Chroma para continuar offline; o limiar foi
  calibrado com poucas perguntas e deve ser reavaliado se o manual crescer.
