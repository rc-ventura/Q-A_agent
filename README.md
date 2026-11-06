# Empório da Música — Agente de Atendimento Virtual

Agente de atendimento ao cliente de uma loja de instrumentos musicais fictícia (Campo Grande/MS), feito para o desafio técnico de AI Engineer da Artefact. Ele responde, em português, sobre **catálogo, preço, estoque e promoções**, **políticas da loja** (trocas, pagamento, frete, garantia, horários) e **status de pedidos**, e recusa com cordialidade o que está fora do escopo.

A decisão central do desafio, saber quando consultar **dados** e quando consultar **políticas**, é explícita na interface: cada consulta aparece como um bloco recolhível ("Consultando catálogo…", "Consultando políticas…", "Consultando pedidos…").

## Prova de funcionamento

As **5 conversas de exemplo** pedidas no desafio estão em [`examples/`](examples/) (texto, geradas pelo agente real). As capturas abaixo são a prova na interface e complementam essas conversas; não são conversas adicionais.

Capturas da UI rodando o agente real (`gpt-4o-mini`) em 2026-11-05 e 2026-11-06 (a imagem 6), sem edição das respostas. Os fatos de cada resposta foram conferidos contra os CSVs e o PDF; as mesmas perguntas estão automatizadas na bateria de eval (`uv run pytest -m eval`).

| O desafio pede | Evidência |
|---|---|
| Consultar **dados** (disponibilidade, preço) | [1](#1-catálogo-filtro-por-categoria-e-preço) violões até R$ 1.000 com estoque; [4](#4-memória-da-conversa-dado-e-política-na-mesma-conversa) preço do Takamine GD20 |
| Consultar **políticas** (troca, pagamento) | [2](#2-política-de-devolução-por-arrependimento) devolução por arrependimento; [4](#4-memória-da-conversa-dado-e-política-na-mesma-conversa) parcelamento |
| Informações gerais da loja (endereço) | [6](#6-informação-geral-da-loja) endereço e CEP conferidos com o manual |
| Saber **quando** usar cada fonte | blocos "Consultando catálogo…", "Consultando políticas…", "Consultando pedidos…" em 1 a 4 |
| Status de pedido | [3](#3-pedido-identificação-antes-de-expor-dados) identificação por nome antes de mostrar pedidos, com motivo do cancelamento |
| **Fora do escopo** e **persona** | [5](#5-acessórios-fora-do-escopo-e-reclamação) acessórios, pergunta alheia à loja, reclamação com prazo de retorno |
| Situação **não trivial** | [2](#2-política-de-devolução-por-arrependimento) regra do manual aplicada; [4](#4-memória-da-conversa-dado-e-política-na-mesma-conversa) "e dá pra parcelar?" resolvido pelo contexto da mensagem anterior |
| Configuração do provedor sem editar arquivos | [0](#0-configuração-da-chave-no-primeiro-acesso) tela de chave, com validação |

#### 0. Configuração da chave no primeiro acesso

Sem `OPENAI_API_KEY`, o app abre nesta tela. A chave é validada na OpenAI antes de ser gravada; aqui, uma chave inválida de demonstração.

![Tela de configuração da chave com erro de chave inválida](docs/images/00-onboarding-chave.png)

#### 1. Catálogo: filtro por categoria e preço

"Violões até R$ 1.000" vira filtro SQL (categoria, preço, estoque > 0). Os cinco produtos, preços e estoques são os do `products.csv`.

![Lista de violões até R$ 1.000 com preço e estoque](docs/images/01-catalogo-violoes.png)

#### 2. Política de devolução por arrependimento

Resposta tirada da seção 4.1 do manual: 7 dias corridos, embalagem original, reembolso em até 10 dias úteis, frete de devolução pago pela loja.

![Resposta sobre devolução por arrependimento](docs/images/02-politica-arrependimento.png)

#### 3. Pedido: identificação antes de expor dados

O agente pede nome completo ou e-mail (nunca telefone) e só então lista os pedidos: #19 cancelado por pagamento não confirmado e #1 entregue com rastreio BRAB1234567BR.

![Consulta de pedidos com identificação do cliente](docs/images/03-pedido-identificacao.png)

#### 4. Memória da conversa: dado e política na mesma conversa

A segunda pergunta não repete o produto; o agente usa o histórico (checkpointer SQLite) e aplica a regra de parcela mínima de R$ 100.

![Preço do Takamine GD20 seguido de pergunta sobre parcelamento](docs/images/04-multiturno-dados-e-politica.png)

#### 5. Acessórios, fora do escopo e reclamação

A loja só vende instrumentos; pergunta alheia recebe recusa cordial; reclamação recebe empatia e o prazo de retorno de 24 horas úteis.

![Recusa de acessórios, recusa fora do escopo e tratamento de reclamação](docs/images/05-escopo-persona-reclamacao.png)

#### 6. Informação geral da loja

"Qual o endereço da loja?" consulta o manual de políticas e devolve o endereço e o CEP exatamente como estão na seção 1 do PDF (Rua 14 de Maio, 3200, Centro, Campo Grande/MS, CEP 79202-333).

![Resposta com o endereço da loja](docs/images/06-endereco-da-loja.png)

## Como rodar

Você precisa de uma chave da API da OpenAI (enviada por e-mail pelo autor). Ela é colada na tela de configuração do app no primeiro acesso: não é preciso editar arquivos.

### Opção A — Docker (recomendada)

```bash
git clone <url-do-repositorio> && cd <repositorio>
docker compose up --build -d
```

Abra <http://localhost:7860>, cole a chave e clique em **Salvar e começar**. O app valida a chave, grava no `.env` local do container, prepara os dados (CSVs no SQLite e manual de políticas no índice vetorial) e libera o chat.

Se já existir um `.env` com `OPENAI_API_KEY` na pasta do projeto, o compose o usa e a tela de configuração é pulada.

### Opção B — Local

Requer Python 3.11+ e [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python -m app          # http://127.0.0.1:7860
```

A chave pode ser colada na tela inicial ou colocada antes em um `.env` (`cp .env.example .env`).

### Variáveis de ambiente

| Variável | Padrão | Função |
|---|---|---|
| `OPENAI_API_KEY` | — | Chave da OpenAI (também configurável pela UI) |
| `OPENAI_MODEL` | `gpt-4o-mini` | Modelo de chat |
| `OPENAI_TEMPERATURE` | `0` | Temperatura do modelo (atendimento determinístico) |
| `RAG_MIN_SCORE` | `0.30` | Similaridade mínima para um trecho do manual ser usado |

### Testes

```bash
uv run pytest            # testes unitários, offline (ingestão, tools, UI, prompts)
uv run pytest -m eval    # bateria contra o agente real (usa a chave; gasta centavos)
```

Roteiro manual de validação: [`specs/001-store-qa-agent/quickstart.md`](specs/001-store-qa-agent/quickstart.md). Conversas de exemplo: [`examples/`](examples/).

## Arquitetura

```
Gradio (app/)  ──►  Dispatcher (create_agent, persona + regras)
                       │  4 tools-roteadoras, uma por especialista
        ┌──────────────┼───────────────┬────────────────┐
     catálogo       políticas        pedidos         atendimento
   search_products  search_policies  find_customer   (sem tools de dados:
   get_product_     get_store_info   list_customer_   persona, escopo,
   details              │             orders          reclamações)
        │               │                │
   SQLite (somente   ChromaDB          SQLite (somente
   leitura)          (manual em PDF)   leitura)

Memória da conversa: AsyncSqliteSaver (um thread_id por conversa)
```

- `agent/` — dispatcher (`graph.py`, `prompt.py`), especialistas (`specialists/`), tools (`tools/`), ingestão (`ingest.py`, `policies_rag.py`).
- `app/` — UI Gradio e fluxo de configuração da chave.
- `data/source/` — os 6 CSVs e o PDF do desafio; `data/runtime/` é gerado (SQLite, índice vetorial, checkpoints) e fica fora do git.
- `docs/adrs/` — decisões arquiteturais; `docs/learning-lessons/` — falhas e achados; `specs/` — spec, plano, tarefas e contratos.

## Decisões técnicas e por quê

**Framework: `langchain.agents.create_agent` sobre o runtime LangGraph.** Um agente com tool calling cobre o problema sem o peso de um harness maior. O `deepagents` foi avaliado e descartado: planejamento, filesystem virtual, subagentes e shell não têm uso neste domínio e seriam superfície a podar ([ADR-0003](docs/adrs/0003-right-sizing-harness.md)). O LangGraph dá o checkpointer e o `langgraph.json`, que permite subir o mesmo grafo no Agent Server oficial se a escala exigir.

**Dispatcher + especialistas ([ADR-0004](docs/adrs/0004-arquitetura-dispatcher.md)).** Um roteador leve delega a especialistas de domínio, um por user story, cada um com prompt e tools próprios e testável isoladamente. Torna o roteamento dados-vs-políticas visível na UI. O custo é real: cada pergunta passa por dois modelos (roteador e especialista) e o roteador reescreve a resposta, o que soma latência e tokens.

**LLM: OpenAI `gpt-4o-mini`.** Tool calling maduro e custo baixo por conversa. Temperatura 0 em todos os agentes: atendimento não precisa de criatividade, e a bateria mostrou o efeito (abaixo). A chave é colada na tela inicial, validada na OpenAI antes de ser gravada no `.env` local (permissão 0600), mascarada no `repr` das configurações e nunca aparece em logs nem em mensagens de erro ([ADR-0006](docs/adrs/0006-chave-openai-pela-ui-gravada-no-env.md)).

**Retrieval híbrido ([ADR-0002](docs/adrs/0002-arquitetura-hibrida-tools-rag.md)).** Dados tabulares (preço, estoque, pedidos) vão por function calling sobre SQLite aberto somente para leitura: filtros e contas exatos, sem depender de embedding. Texto livre (o manual de políticas) vai por RAG: chunking por seção numerada do manual, título da seção embutido no vetor, IDs determinísticos, limiar mínimo de similaridade e sinal explícito de recuperação fraca para o agente declarar o limite em vez de improvisar. Embeddings `text-embedding-3-small` em espaço cosseno: nas 12 perguntas de política da bateria a seção correta ficou no top-3 em 12/12, contra 8/12 do modelo padrão do Chroma, que é em inglês ([ADR-0005](docs/adrs/0005-embeddings-openai-no-indice-de-politicas.md)).

**Estratégia de prompt.** O roteador tem as regras duras (nunca inventar preço/estoque, nada de ações transacionais, recusa de fora de escopo) e é obrigado a delegar; perguntas mistas acionam todos os especialistas envolvidos. Cada especialista tem regras do seu domínio (promoção sempre com preço original, percentual e preço final; citar o manual literalmente; identificar o cliente por nome completo ou e-mail antes de mostrar pedidos). As regras são verificadas por testes de marcadores nos prompts e, principalmente, pela bateria de eval.

**Persistência e deploy ([ADR-0001](docs/adrs/0001-runtime-single-container.md)).** Um único processo e um único container: UI, agente e `AsyncSqliteSaver` juntos. Para um avaliador isso significa uma chave, um comando e nenhum Postgres/Redis a subir. O SQLite e o índice vetorial são derivados dos CSVs e do PDF e reconstruídos a cada inicialização, então um volume antigo nunca serve dados de versão anterior ([ADR-0007](docs/adrs/0007-dados-de-runtime-reconstruidos-a-cada-start.md)).

## Qualidade e o que a avaliação revelou

O desenvolvimento seguiu TDD, e o critério de aceite é a bateria contra o agente real ([ADR-0008](docs/adrs/0008-bateria-de-eval-com-llm-real-como-aceite.md)). Os testes unitários rodam offline (`uv run pytest`). A bateria de eval (`uv run pytest -m eval`) roda as perguntas-ouro do quickstart contra o agente real, com asserções de fatos-chave, resposta em até 30 s e cenários de acompanhamento com referência anafórica.

Resultado na versão final: **43 de 43 casos** (11 de catálogo, 12 de políticas, 14 de pedidos, perguntas mistas, acompanhamento multi-turno e cenários da spec, e 6 de persona e escopo), cada resposta em até 30 s, em duas rodadas completas consecutivas (4 min 08 s e 3 min 46 s). Antes de fixar a temperatura em 0, o número variava: as rodadas completas desta fase deram 41/43, 40/43, 43/43, 42/43, 42/43, 41/43 e 41/43 (em ordem; houve ajustes de prompt e de código entre algumas), sempre com falhas em casos diferentes (variação do `gpt-4o-mini`; cada caso falhava em poucos por cento das vezes, e 43 casos somam cerca de 1 a 2 falhas por rodada). Casos que falharam uma vez na bateria completa foram medidos isoladamente 10 vezes e deram 10/10, o que confirma variância e não defeito: frete para Manaus (9/10 antes de um ajuste de prompt, 10/10 depois), LGPD de exclusão, cliente desconhecido, recusa de acessórios, Black Friday inativa e parcelamento no preço. Os casos de fronteira também foram medidos 10 vezes cada, e o que ficou abaixo de 9/10 virou correção com teste: Black Friday inativa (8/10 para 10/10, regra de primeira frase no especialista de catálogo), parcelamento no preço de um produto (8/10 para 10/10, o dispatcher passou a chamar políticas sempre que a mensagem citar pagamento) e `get_product_details` que não aceitava "ukulele Kalani KAL-700T" (a categoria antes do modelo; defeito da tool, 7/10 para 10/10 no especialista). Com temperatura 0, duas rodadas completas seguidas deram 43/43. As saídas completas das quatro rodadas de 2026-11-06 e o registro das medições isoladas estão em [`reports/eval-runs/`](reports/eval-runs/README.md).

Um ponto de atenção medido: na pergunta "se eu comprar no PIX, ganho mais 5% em cima da promoção?", com a temperatura padrão do modelo o agente omitia a regra de não cumulatividade em cerca de 1 de cada 5 execuções (14 de 18 medidas), porque às vezes o dispatcher respondia só com o catálogo. Com temperatura 0 foram 20 de 20. A amostra é pequena, e o caso continua na bateria.

Fluxo do avaliador validado a partir de um clone limpo (sem `.env`): `docker compose up --build`, onboarding da chave e primeira resposta em 26 s com cache de camadas; o build a frio levou cerca de 2 minutos.

A primeira execução da bateria, com todos os testes unitários verdes, falhou em 11 de 36 casos. As causas, registradas em [LL-0002](docs/learning-lessons/0002-eval-do-quickstart-revelou-roteamento-e-recuperacao.md): o roteador respondendo sozinho em vez de delegar, embeddings em inglês, produto descontinuado invisível ao agente, filtro de categoria que não tolerava "violao" e itens de pedido com quantidade errada ("7 unidades" num pedido de 1). Todas foram corrigidas com teste. Esta última teve o diagnóstico corrigido na validação final: a causa não era o modelo, e sim a ingestão duplicando `order_items` a cada start do app. A lição prática: testes unitários não substituem avaliar o agente de ponta a ponta.

## Suposições assumidas

O enunciado pede que ambiguidades sejam resolvidas por uma interpretação razoável e documentada. As que adotei:

- **Idioma:** todo o atendimento é em português do Brasil, como os dados, o manual e o público da loja.
- **Uso dos dados:** usei todos os arquivos (os 6 CSVs e o PDF). O enunciado dispensa usar tudo, mas a cobertura completa permite responder preço, estoque, pedido e política na mesma conversa.
- **Identificação do cliente:** por nome completo ou e-mail, nunca por telefone, e sem autenticação forte. É aceitável para um protótipo e está listada nas limitações.
- **Canal:** a interface web simula o atendimento. Integrar o WhatsApp real está fora do escopo.
- **Ações transacionais:** o agente não cancela, altera nem reembolsa pedidos. Ele explica a regra e encaminha ao atendimento humano.
- **Horário de resposta:** o agente responde a qualquer hora. Quando a dúvida depende de uma pessoa, informa o horário de funcionamento e o prazo de retorno do manual.
- **Valores que as fontes não trazem** (por exemplo, o frete para uma cidade específica): o agente diz que o valor não consta, explica o que o manual diz sobre o cálculo e indica o contato da equipe. Ele não estima.
- **Conflitos entre fontes:** o manual traz dois números de WhatsApp (seção 1.2 e seção 7), e o agente usa o da seção 1.2. Nos pedidos #3 e #20, o total registrado difere da soma dos itens (R$ 3.450,00 contra R$ 3.498,00, e R$ 1.400,00 contra R$ 1.488,00; os dados não dizem o motivo), e o agente informa o total do pedido.
- **Status de produto:** além de `active` e `inactive`, os dados têm `discontinued` e `coming_soon`, e o agente trata cada um: produto descontinuado sai do catálogo e o agente oferece modelos equivalentes em estoque; produto em breve (`coming_soon`) é informado como ainda indisponível, sem confirmar estoque nem preço.

## Limitações conhecidas

- **Identificação do cliente é só uma regra de prompt.** O agente pede nome completo ou e-mail, mas a tool `list_customer_orders` aceita qualquer `customer_id`, sem vínculo com o cliente que se identificou, e a busca por nome é por trecho (mínimo de 3 letras, no máximo 5 candidatos). Quem souber o nome de outra pessoa vê os pedidos dela, e uma mensagem forjada para o modelo (prompt injection) poderia pedir pedidos por ID. A busca devolve só nome e cidade para minimizar exposição, mas isso não é autenticação.
- **Sem controle de acesso à configuração da chave.** Quem alcança a porta 7860 pode trocar a chave, inclusive pela API do Gradio mesmo com a tela já oculta. Por isso o `docker-compose.yml` publica a porta só em `127.0.0.1`; para expor em rede seria preciso autenticação.
- **Sem limite de taxa nem de gasto.** Qualquer um que use a interface consome a chave da OpenAI, sem teto por sessão.
- **Dependências com avisos conhecidos, não alcançáveis aqui.** `pip-audit` aponta avisos no Pillow (transitivo do Gradio, o app não recebe imagens) e no chromadb (carregamento remoto de modelos e autorização do modo servidor; o app usa o cliente embarcado). Devem ser atualizados quando houver versão corrigida.
- **Imagem Docker roda como root e sem `HEALTHCHECK`.** Aceitável para uma demonstração local.
- **Retenção ilimitada.** Os checkpoints de conversa ficam no SQLite sem expiração nem rotina de limpeza, e guardam o que o cliente escreveu.
- **Pensado para uma conversa por vez.** Cada conversa tem seu próprio `thread_id`, mas não houve teste de carga ou de concorrência alta; SQLite e um único processo não foram dimensionados para isso.
- **A chave não sobrevive a `docker compose down`.** Só `data/runtime/` está em volume; o `.env` gravado pela tela vive no sistema de arquivos do container e é recriado por `down` + `up`. `restart` e `stop`/`start` preservam.
- **Não há integração com WhatsApp real**, só a interface web; o manual menciona o canal.
- **Respostas de LLM podem variar.** Com temperatura 0 a variação cai muito (duas rodadas completas de 43 casos deram 43/43), mas não some: o modelo não é determinístico por contrato, e uma mudança de versão do modelo pode alterar o comportamento. Antes da temperatura 0, as rodadas deram de 40/43 a 43/43. Não há garantia de 100% por execução.
- **Fontes com inconsistências.** O manual traz dois números de WhatsApp (seção 1.2 e seção 7); o agente usa o da seção 1.2. O `data-model.md` previa só `active`/`inactive` para produtos, mas os dados têm também `discontinued` e `coming_soon`.
- **Limiar de similaridade calibrado com poucas perguntas** (12 relevantes e 8 sem relação, medidas uma vez). Deve ser reavaliado se o manual crescer.

## O que eu faria com mais tempo

- Eliminar o segundo salto de LLM: repassar a resposta do especialista direto (com streaming dos tokens dele) quando o roteador não precisa reescrever, reduzindo latência e custo.
- Autenticação real para pedidos (e-mail mais código de verificação), `customer_id` vinculado ao cliente identificado na sessão, e limite de tentativas e de gasto por sessão.
- Imagem Docker sem root, com `HEALTHCHECK`, e atualização do Pillow e do chromadb quando houver versão corrigida.
- Reaproveitar um único grafo e um único checkpointer entre requisições, em vez de recriá-los a cada mensagem.
- Avaliação mais robusta: juiz LLM para qualidade de tom, múltiplas execuções por caso para medir variância, testes de prompt injection e de tentativa de extrair dados de outros clientes.
- Observabilidade (traces por turno com LangSmith ou OpenTelemetry) e CI rodando unitários a cada push e a bateria sob demanda.
- Checkpointer em Postgres com expiração configurável, e persistência da chave fora do container.
- Handoff para atendimento humano de verdade, em vez de apenas informar o telefone.

## Uso de assistentes de IA no desenvolvimento

O projeto foi feito com **Spec-Driven Development** usando o Spec Kit (constituição, especificação, plano, tarefas, implementação). O Spec Kit foi inicializado com a integração do **Devin** (`.specify/integrations/devin.manifest.json`); depois as skills foram migradas para o **Claude Code** (`.claude/skills/`), com conteúdo idêntico. O **Claude Code** (Anthropic) foi o assistente que escreveu a maior parte do código, dos testes e da documentação (só parte dos commits traz o trailer `Co-Authored-By`; os mais antigos não o têm, então o histórico não separa sozinho o que o assistente escreveu), sempre sob TDD e com a documentação oficial das bibliotecas consultada antes de codificar.

Na etapa final, a revisão (`reports/sdd-final-review/`) rodou como três papéis, QA, Segurança e Tech Leader, executados por subagentes do Claude Code. Os relatórios são análise de modelo, não auditoria humana: cada achado foi reproduzido ou refutado com teste ou medição antes de virar correção. A segunda opinião externa via Devin CLI não ocorreu: ele estava instalado, mas recusou chamadas de ferramenta em modo não interativo. As decisões de escopo e arquitetura (um container, abordagem híbrida, arquitetura dispatcher, OpenAI como provedor, UI web com tela de chave) foram do autor e estão registradas na spec e nos ADRs. A verificação não confiou na saída dos assistentes: os fatos dos exemplos e das asserções foram conferidos contra os CSVs e o PDF, e os defeitos que a avaliação encontrou (inclusive nos próprios testes escritos com ajuda de IA) estão documentados no [LL-0002](docs/learning-lessons/0002-eval-do-quickstart-revelou-roteamento-e-recuperacao.md).
