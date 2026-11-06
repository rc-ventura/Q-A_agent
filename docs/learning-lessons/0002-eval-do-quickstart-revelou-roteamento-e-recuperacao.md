# LL-0002: A bateria de eval achou o que os testes unitários não podiam achar

Data: 2026-11-05. Contexto: T042 (bateria do quickstart contra o agente real). Referências: ADR-0004, ADR-0005, LL-0001.

## O que aconteceu

Os 76 testes unitários estavam verdes e a primeira execução da bateria falhou em 11 de 36 casos.
O diagnóstico exigiu rastrear o que cada camada fazia, e não só ler a resposta final:

1. **Roteamento do dispatcher.** O prompt tinha a saída "se nenhuma rota servir, responda você
   mesmo". O gpt-4o-mini a usava para recusar perguntas de política ("não consigo informar prazos de
   entrega") sem consultar ninguém. Chamar o especialista direto dava a resposta certa. A correção foi
   remover a saída, exigir delegação em toda mensagem que não seja saudação e mandar chamar todos os
   especialistas nas perguntas mistas.
2. **Embedding em inglês.** O MiniLM padrão do Chroma deixava a seção certa fora do top-3 em 4 de 12
   perguntas em português (ADR-0005). O LL-0001 já tinha achado dois bugs de métrica no mesmo índice;
   a causa de fundo era o modelo.
3. **Produto descontinuado invisível.** O SQL do catálogo filtrava `status = 'active'`, então o
   agente dizia "não localizei" para um item que o manual (§7.3) manda tratar como "não faz mais
   parte do catálogo". O detalhe do produto agora expõe o status; a busca continua só com ativos.
4. **Teste vazando segredo.** Um `assert` falho em `test_defaults` imprimiu o `repr` completo de
   `Settings`, incluindo a chave real, porque o teste não isolava o `.env`. `openai_api_key` agora é
   `SecretStr` e os testes usam `Settings(_env_file=None)`.

5. **Regra nova que invade o vizinho.** Para garantir o prazo de 24 h nas reclamações (medido em 7/10),
   uma primeira regra ampla no roteador fez "Me arrependi, posso devolver?" e "veio com defeito, em quanto
   tempo posso trocar?" virarem reclamações: a bateria pegou a regressão na rodada seguinte. A versão
   final distingue relato de problema (sem pergunta de regra) de pergunta de regra, e foi medida 10 vezes
   por caso (10/10 nos quatro casos de fronteira).
6. **Exemplos de conversa também são teste.** Ao capturar as conversas de exemplo do agente real e conferir
   cada fato contra os dados, apareceram três defeitos que a bateria não cobria: pedido de telefone para
   identificar o cliente, "7 unidades" num pedido de 1 unidade e oferta de acessórios. Cada um virou teste.
7. **Diagnóstico errado no item 6, achado na validação final.** As "7 unidades" foram atribuídas ao
   modelo inventando a quantidade, e a correção foi expor `quantity` no tool. Na validação contra a spec,
   um caso novo mostrou "11 unidades" para outro pedido de 1 unidade, já com o campo exposto. A causa
   real estava na ingestão: `order_items` não tem chave primária, o `INSERT OR REPLACE` só acrescenta, e
   o boot (T040) reingere a cada start. O banco local tinha cada item 11 vezes; o modelo somava as linhas
   repetidas. As "7 unidades" eram, muito provavelmente, a mesma duplicação com 7 starts. A ingestão agora
   esvazia as tabelas antes de recarregar, com teste de reingestão tripla. O mesmo caso mostrou o status
   cru `"shipped"` para o cliente; o tool passou a devolver status e forma de pagamento em português.

## Inconsistências nas fontes (não corrigidas, registradas)

- O quickstart dizia que Pedro Henrique Oliveira tem os pedidos #3 e #19; nos CSVs são #1 e #19 (o #3
  é de outra cliente). Corrigido no quickstart.
- O manual traz dois WhatsApp: (67) 3341-4444 na seção 1.2 e (67) 3321-4500 na seção 7. O agente usa o
  da seção 1.2; a bateria não assere o número para não depender do trecho recuperado.
- O `data-model.md` prevê `status` apenas `active`/`inactive`; os dados têm também `discontinued` e
  `coming_soon`.

## Como evitar

- Tratar a bateria de eval como parte do ciclo TDD de qualquer mudança em prompt, tool ou índice.
- Depurar agentes em camadas: chamar o especialista sozinho separa falha de roteamento de falha de
  recuperação em um passo.
- Medir o retrieval com perguntas reais antes de ajustar prompts; ajustar prompt para compensar
  embedding ruim só desloca o problema.
- Nunca deixar objetos de configuração com segredo sem mascaramento: o pytest imprime `repr` em falhas.
- Conferir os dados antes de escrever fatos esperados a partir da spec.
- Mudança de prompt em um comportamento exige medir os casos vizinhos, não só o alvo: repetir cada caso
  de fronteira ~10 vezes antes de aceitar. Uma única rodada verde esconde a variância do modelo.
- Quando o modelo inventa um dado, perguntar primeiro se o tool o entregou. Expor o campo no tool vale mais
  do que mais uma frase de "não invente" no prompt.
- Antes de culpar o modelo, olhar o dado que ele recebeu no banco real, não só no banco do teste. Os
  testes unitários ingeriam uma vez em banco novo e nunca veriam a duplicação: testar a operação como
  ela roda em produção (aqui, reingestão repetida).
