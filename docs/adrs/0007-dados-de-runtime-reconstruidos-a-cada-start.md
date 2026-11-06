# ADR-0007: Dados de runtime derivados das fontes e reconstruídos a cada inicialização

## Status
Aceito (2026-11-05). Complementa D3 e D8 do `research.md`.

## Contexto
O agente lê de dois artefatos derivados: o SQLite operacional (dos 6 CSVs) e o índice Chroma (do PDF
do manual). Ambos ficam em `data/runtime/`, que é volume no Docker e sobrevive a reinícios. É preciso
decidir quando reconstruí-los e o que fazer com o que já existe.

Alternativas consideradas:

- Construir só se não existir: rápido, mas uma mudança nos CSVs, no PDF, no modelo de embedding ou na
  métrica de distância nunca chegaria a um volume antigo (o ADR-0005 trocou os dois últimos).
- Comando de ingestão separado: mais um passo para o avaliador e mais um jeito de esquecer.
- Reconstruir a cada start: custo de cerca de 1 s para o SQLite e uma chamada de embedding para ~35
  trechos.

## Decisão
As fontes em `data/source/` são a única verdade, e a cada inicialização (e após configurar a chave):

- o SQLite é **esvaziado e recarregado** tabela a tabela, com validação Pydantic por linha;
- o índice de políticas é **apagado e recriado** com IDs determinísticos.

Quem consulta precisa tolerar a reconstrução: a tool de políticas mantém a collection em cache e, se
ela tiver sido recriada (`NotFoundError`), reabre uma vez e repete a busca.

## Consequências
- Positivas: o volume nunca fica com dados ou embeddings de versão anterior; nenhuma migração.
- Negativas: a reconstrução exige chave e rede para os embeddings; o primeiro start após configurar a
  chave leva alguns segundos a mais.
- Neutras: a decisão expôs dois defeitos corrigidos com teste (LL-0002, item 7). `order_items` não tem
  chave primária, e `INSERT OR REPLACE` duplicava os itens a cada start, até a ingestão passar a
  esvaziar as tabelas. O handle da collection em cache também ficava inválido após a reindexação. Os
  testes cobrem agora a operação como ela roda: reingestão repetida e consulta após reindexar.
