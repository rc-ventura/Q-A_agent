# ADR-0008: Bateria de eval contra o agente real como critério de aceite

## Status
Aceito (2026-11-05).

## Contexto
Os critérios de sucesso da spec (SC-001 a SC-003, SC-007) falam do comportamento do agente:
precisão de preço e política, recusa de escopo, latência. Testes unitários cobrem tools, ingestão e
prompts, mas não o que o modelo faz com eles. Com todos os unitários verdes, a primeira rodada contra
o agente real falhou em 11 de 36 casos (LL-0002).

Alternativas consideradas:

- Só testes unitários com LLM simulado: rápidos e determinísticos, mas cegos a roteamento,
  recuperação e alucinação, justamente as falhas observadas.
- Juiz LLM avaliando cada resposta: mede tom e qualidade, mas acrescenta um segundo modelo com sua
  própria variância e custo, e uma nota em vez de um fato verificável.
- Asserções de fatos-chave sobre a resposta real: verificáveis contra os CSVs e o PDF, baratas e
  legíveis.

## Decisão
Uma bateria `pytest` marcada `eval` roda as perguntas da spec e do quickstart contra o agente real.
Cada caso declara os fatos obrigatórios (grupos de grafias aceitas, como "12x" ou "12 vezes"), os
proibidos (valores inventados, dados de outro cliente) e o limite de 30 s. Os fatos esperados são
tirados das fontes, não da spec. A bateria fica fora do `pytest` padrão (`addopts = -m 'not eval'`)
porque exige chave, rede e gasta centavos. Mudança em prompt ou tool só é aceita após rodá-la, e casos
de fronteira de roteamento são repetidos 10 vezes antes de aceitar.

## Consequências
- Positivas: achou defeitos que nenhum unitário acharia (roteamento, embedding em inglês, itens
  duplicados, status em inglês); cada critério de sucesso tem um teste executável.
- Negativas: não é determinística. Uma rodada pode falhar por variância do modelo, e um caso de
  fronteira medido em 10/10 deu 9/10 numa medição seguinte. A asserção por substring não avalia tom
  nem pega uma resposta certa mas mal formulada. Com a temperatura padrão cada caso falhava em poucos
  por cento das vezes, o que dava 1 a 2 falhas por rodada de 43 casos, em casos diferentes. Fixar a
  temperatura em 0 (`OPENAI_TEMPERATURE`) tornou duas rodadas seguidas 43/43. Isso reduz a variância, mas
  não a elimina, e as asserções por substring também geraram falsos negativos (uma recusa correta com
  "não comercializa" fora da lista de grafias aceitas), corrigidos ampliando a lista.
- Neutras: não roda em CI sem segredo; o README documenta como rodar e os números da última execução.
