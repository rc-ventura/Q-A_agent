# Feature Specification: Agente de Atendimento Virtual — Empório da Música

**Feature Branch**: `001-store-qa-agent`

**Created**: 2026-11-03

**Status**: Draft

**Input**: User description: "Desafio Técnico AI Engineer 2026 (Artefact): prototipar um agente de mensagens de texto em Python para o atendimento da loja fictícia Empório da Música, usando os CSVs operacionais (produtos, categorias, pedidos, itens, clientes, promoções) e o manual de políticas da loja (PDF). O agente deve assumir a persona da loja, saber quando consultar dados vs. políticas, lidar com perguntas fora de escopo, e ser entregue em repositório público com README justificado e 3-5 conversas de exemplo."

## Contexto do Problema

A Empório da Música é uma loja fictícia de instrumentos musicais em Campo Grande/MS cuja equipe de atendimento está sobrecarregada com perguntas recorrentes (horários, status de pedido, preço e disponibilidade de produtos). O agente de atendimento virtual deve absorver esse volume, respondendo com precisão a partir das fontes oficiais da loja (dados operacionais + manual de políticas), mantendo o tom de voz da marca.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consulta de catálogo, preço e disponibilidade (Priority: P1)

O cliente pergunta sobre produtos do catálogo — exemplos: "Quais opções de violões custando até R$ 1.000?", "Quanto custa o Takamine GD20?", "Vocês têm bateria em estoque?". O agente consulta os dados atuais da loja e responde com nome, preço, disponibilidade e, quando houver promoção ativa, exibe preço original + percentual de desconto + preço final.

**Why this priority**: É a maior fonte de perguntas recorrentes e o cenário principal do desafio. Precisão aqui é crítica — informação incorreta de preço/estoque configura propaganda enganosa (citado no próprio manual). Sozinha, esta história já entrega um MVP útil.

**Independent Test**: Enviar "Quais opções de violões disponíveis custando até R$1000?" e verificar que a resposta lista somente produtos reais da categoria Violões com preço ≤ R$ 1.000 e estoque > 0, sem nenhum dado inventado.

**Acceptance Scenarios**:

1. **Given** o catálogo carregado, **When** o cliente pergunta "Quanto custa o Takamine GD20?", **Then** o agente responde R$ 2.199,00 com disponibilidade atual (5 unidades em estoque), sem inventar dados.
2. **Given** um produto com promoção ativa (ex.: promoção `is_active=1` para o produto 127, 10%), **When** o cliente pergunta o preço, **Then** a resposta mostra preço original, percentual de desconto e preço final — nunca apenas o preço promocional isolado.
3. **Given** um produto sem estoque (ex.: Giannini GF-3D, estoque 0), **When** o cliente pergunta sobre disponibilidade, **Then** o agente informa indisponibilidade temporária e sugere alternativas semelhantes que estejam em estoque.
4. **Given** um produto com promoção inativa (`is_active=0`), **When** o cliente pergunta sobre a promoção, **Then** o agente informa com transparência que a promoção não está vigente e apresenta o preço atual — sem prometer o desconto vencido.

---

### User Story 2 - Políticas e informações institucionais da loja (Priority: P1)

O cliente pergunta sobre horário de funcionamento, endereço, formas de pagamento e parcelamento, trocas e devoluções, frete/prazos de entrega e garantia. O agente responde em conformidade estrita com o manual de políticas da loja (fonte única de verdade para regras).

**Why this priority**: Segunda maior fonte de perguntas recorrentes e onde mora o cenário não trivial exigido nos exemplos de entrega ("Me arrependi da compra, posso devolver meu pedido?"). Erros de política geram prejuízo legal e de experiência.

**Independent Test**: Perguntar "Me arrependi da minha compra, posso devolver meu pedido?" e verificar que a resposta aplica corretamente o direito de arrependimento: 7 dias corridos após o recebimento, produto na embalagem original sem uso, reembolso na mesma forma de pagamento em até 10 dias úteis e frete de devolução por conta da loja.

**Acceptance Scenarios**:

1. **Given** a pergunta "Qual o endereço da loja?", **When** o agente responde, **Then** informa Rua 14 de Maio, 3200 — Centro, Campo Grande-MS (e pode citar telefone/WhatsApp).
2. **Given** a pergunta "Posso parcelar em 12x?", **When** o agente responde, **Then** informa: até 12x sem juros, com parcela mínima de R$ 100, conforme as regras de parcelamento do manual.
3. **Given** a pergunta "Quanto é o frete para Campo Grande?", **When** o agente responde, **Then** informa frete grátis acima de R$ 500, taxa fixa de R$ 35 abaixo disso, e prazo de 1 a 3 dias úteis.
4. **Given** a pergunta "Posso trocar a boquilha do saxofone?", **When** o agente responde, **Then** informa que boquilhas de instrumentos de sopro não são elegíveis para troca, por higiene.

---

### User Story 3 - Acompanhamento de pedido (Priority: P2)

O cliente se identifica (nome completo ou e-mail) e pergunta sobre o andamento do pedido. O agente localiza o cliente, consulta os pedidos dele e informa status, previsão de entrega e código de rastreio quando existir — incluindo explicação transparente em caso de pedido cancelado.

**Why this priority**: Pergunta recorrente clássica do varejo e excelente demonstração de consulta a dados operacionais por entidade (cliente → pedidos), mas depende de identificação do cliente, o que a torna um pouco mais complexa que as anteriores.

**Independent Test**: "Sou Pedro Henrique Oliveira, cadê meu pedido?" → o agente deve encontrar os dois pedidos do cliente 3 (um entregue; um cancelado por pagamento não confirmado) e apresentar ambos com clareza, incluindo o motivo do cancelamento registrado nas notas.

**Acceptance Scenarios**:

1. **Given** um cliente com pedido `shipped` com código de rastreio, **When** ele pergunta pelo pedido, **Then** o agente informa status, código de rastreio e previsão de entrega.
2. **Given** um cliente sem nenhum pedido registrado, **When** ele pergunta pelo pedido, **Then** o agente informa que não encontrou pedidos e oferece ajuda.
3. **Given** uma identificação inexistente ou ambígua nos dados, **When** o cliente pergunta pelo pedido, **Then** o agente solicita um dado adicional (nome completo ou e-mail) em vez de adivinhar — nunca expondo pedidos de outro cliente.

---

### User Story 4 - Persona, escopo e situações especiais (Priority: P3)

O agente mantém consistentemente o tom da Empório da Música (informal mas profissional — "um amigo que entende de música"), redireciona educadamente pedidos de acessórios (que a loja não vende), declina cordialmente assuntos nada relacionados à loja e lida com reclamações com empatia, orientando o encaminhamento ao atendimento humano.

**Why this priority**: Requisito explícito do desafio (persona + escopo), mas só faz sentido sobre o núcleo de perguntas e respostas já funcionando.

**Independent Test**: "Vocês vendem cordas avulsas pro meu violão?" → o agente explica que a loja trabalha exclusivamente com instrumentos e redireciona com educação; "Qual a capital do Canadá?" → recusa cordial, trazendo a conversa de volta ao atendimento.

**Acceptance Scenarios**:

1. **Given** um pedido de acessório (cordas, palhetas, cabos, cases, pedais, amplificadores), **When** o cliente pergunta, **Then** o agente informa que a loja vende apenas instrumentos musicais e redireciona educadamente.
2. **Given** uma pergunta totalmente fora do escopo (clima, política, receitas), **When** o cliente pergunta, **Then** o agente recusa cordialmente e se recoloca à disposição para assuntos da loja.
3. **Given** uma reclamação, **When** o cliente a manifesta, **Then** o agente acolhe com empatia, registra o relato na conversa e informa o prazo de retorno de 24 horas úteis pela equipe.

---

### Edge Cases

- **Mensagem vaga ou ambígua** ("oi", "quero um presente"): o agente conduz perguntas de entendimento antes de consultar dados, em vez de chutar uma intenção.
- **Pergunta mista** (ex.: "Quanto custa o Martin D-28 e dá pra parcelar em 12x?"): combina consulta de dados + política na mesma resposta.
- **Produto não encontrado ou nome aproximado** ("Taylor 214"): o agente interpreta nomes parciais/com erros leves e confirma o produto antes de responder.
- **Informação inexistente nas fontes** (ex.: cotação de frete especial para bateria acústica em outra cidade): o agente segue as faixas do manual, informa a limitação e orienta contato com a equipe — nunca inventa valores.
- **Cliente tenta negociar desconto**: o agente informa que preços seguem tabela e promoções vigentes, sem criar condições inexistentes.
- **Dados conflitantes entre percepção do cliente e sistema** (ex.: cliente afirma que viu promoção ativa): o agente confere o status atual da promoção e responde com transparência.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O agente MUST responder em português do Brasil, com tom informal mas profissional, alinhado à persona da Empório da Música ("um amigo que entende de música"), cumprimentando e encerrando com cordialidade.
- **FR-002**: TODA resposta sobre preço, estoque, disponibilidade e promoções MUST ser baseada em consulta aos dados da loja no momento da resposta. É proibido responder esses pontos a partir de "conhecimento" do modelo — valor inventado é falha crítica.
- **FR-003**: TODA resposta sobre regras (trocas, devoluções, frete, pagamento, garantia, horários, privacidade) MUST ser fiel ao manual de políticas da loja, que é a fonte única de verdade para políticas.
- **FR-004**: O agente MUST distinguir automaticamente o tipo de pergunta e escolher a fonte correta: dados operacionais (catálogo, pedidos, promoções, clientes) vs. manual de políticas vs. combinação de ambos — sem exigir que o cliente saiba dessa separação.
- **FR-005**: Para status de pedido, o agente MUST primeiro identificar o cliente por nome completo ou e-mail; em identificação ambígua ou inexistente, MUST pedir esclarecimento e MUST NOT expor dados de pedidos de outro cliente.
- **FR-006**: Promoções: o agente MUST considerar apenas promoções ativas no momento da resposta; MUST exibir preço original + percentual de desconto + preço final; MUST respeitar a regra de não cumulatividade (desconto PIX de 5% não se aplica sobre preço promocional).
- **FR-007**: Produto fora de estoque: o agente MUST informar indisponibilidade temporária e sugerir alternativas semelhantes em estoque; MUST NOT confirmar disponibilidade sem verificar o estoque atual.
- **FR-008**: Pedidos de acessórios (cordas, palhetas, cabos, cases, pedais, amplificadores) MUST ser educadamente redirecionados, informando que a loja trabalha exclusivamente com instrumentos musicais.
- **FR-009**: Assuntos totalmente fora do escopo da loja MUST receber recusa cordial; o agente MUST NOT responder conteúdo fora do domínio como se fosse um assistente genérico.
- **FR-010**: O agente MUST manter contexto multi-turno dentro da sessão, resolvendo referências de mensagens anteriores ("e o mais barato?", "e em 12x?").
- **FR-011**: Quando a informação solicitada não existir nas fontes disponíveis, o agente MUST declarar a limitação e orientar o contato com a equipe ((67) 3341-4444 / WhatsApp), em vez de alucinar.
- **FR-012**: O agente MUST NOT executar ações transacionais (criar/cancelar pedidos, agendar, alterar dados de clientes): apenas informa, orienta e, quando preciso, encaminha ao atendimento humano.
- **FR-013**: **Entregável** — repositório Git público com histórico de commits refletindo progresso real (não um commit único).
- **FR-014**: **Entregável** — README.md com: instruções completas para rodar o projeto (ambiente, provedor do modelo, comandos); justificativa das decisões técnicas (framework, LLM, arquitetura de retrieval, estratégia de prompt); limitações conhecidas e próximos passos; declaração de uso de assistentes de código/IA e como foram usados.
- **FR-015**: **Entregável** — entre 3 e 5 conversas de exemplo (.md, .txt ou imagem) cobrindo cenários variados, sendo ao menos uma demonstrando situação não trivial (consulta a dados em tempo real ou aplicação de regra do manual).
- **FR-016**: A UI MUST oferecer, no primeiro acesso (ou quando a chave não estiver configurada), um campo para o usuário colar a chave da API do provedor de LLM; ao confirmar, o sistema grava a chave no arquivo `.env` local e inicia o chat — sem que o usuário edite arquivos manualmente. A chave MUST ficar apenas no ambiente local do usuário e MUST NOT ser commitada no repositório (o `.env` deve estar no `.gitignore`).

### Technical Decisions Originating from the Challenge

- **TD-001**: Linguagem principal obrigatória: **Python** (única restrição técnica do desafio).
- **TD-002**: Abordagem do agente: **híbrida — function calling/tools para os dados operacionais (CSVs de produtos, pedidos, clientes, promoções) + RAG sobre o manual de políticas (PDF)**. Decidido em 2026-11-03: reflete fielmente a separação "dados vs. políticas" pedida no enunciado, garante precisão em cálculos/filtros sobre dados tabulares e demonstra a decisão arquitetural ao avaliador.
- **TD-003**: Interface de interação: **UI web simples** com tela de chat. Decidido em 2026-11-03: inclui uma tela inicial de configuração em que o usuário cola a chave da API e o próprio app grava a configuração (arquivo `.env`) — sem edição manual de arquivos.
- **TD-004**: Modelo e provedor de LLM: **OpenAI via API (paga)**. Decidido em 2026-11-03: o autor do projeto gera uma chave dedicada para o avaliador; o provisionamento da chave acontece pela própria UI (ver TD-003 e FR-016).

### Key Entities

- **Cliente**: pessoa atendida; atributos: nome, telefone, e-mail, cidade. Relaciona-se com Pedidos.
- **Produto**: instrumento musical do catálogo; atributos: nome, preço (BRL), categoria, descrição, especificações, estoque, status. Relaciona-se com Categoria, Itens de Pedido e Promoções.
- **Categoria**: família de instrumentos (guitarras, violões, baterias etc.).
- **Pedido**: compra de um cliente; atributos: data, status (pending/confirmed/shipped/delivered/cancelled), total, forma de pagamento, código de rastreio, previsão de entrega, notas.
- **Item de Pedido**: vínculo pedido ↔ produto com quantidade.
- **Promoção**: desconto percentual sobre um produto, com descrição da campanha e indicador de ativa/inativa.
- **Manual de Políticas**: documento oficial da loja (horários, pagamento, trocas, frete, promoções, garantia, privacidade) — fonte única de verdade para regras de negócio.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das respostas sobre preço, estoque, disponibilidade e promoções correspondem exatamente aos dados atuais das fontes, em uma bateria de pelo menos 10 perguntas de catálogo — zero valores inventados.
- **SC-002**: 100% das respostas sobre políticas são consistentes com o manual (trocas, frete, pagamento, horários, garantia), em uma bateria de pelo menos 10 perguntas de políticas.
- **SC-003**: 100% das perguntas fora de escopo recebem redirecionamento ou recusa cordial, sem conteúdo inventado.
- **SC-004**: Nos cenários primários, o cliente obtém uma resposta útil em no máximo 2 trocas de mensagem (contando a pergunta inicial).
- **SC-005**: São entregues pelo menos 3 conversas de exemplo, com ao menos 1 demonstrando consulta a dados em tempo real ou aplicação de regra do manual.
- **SC-006**: Uma pessoa avaliadora consegue executar o projeto do zero em menos de 15 minutos seguindo apenas o README (clonar, instalar, iniciar a UI, colar a chave na tela de configuração e iniciar a primeira conversa).
- **SC-007**: As respostas do agente chegam em tempo conversacional: no máximo 30 segundos por mensagem em uso normal (bem abaixo do teto de 5 minutos do manual de atendimento).

## Assumptions

- **Idioma**: o atendimento é 100% em português do Brasil (dados, manual e público são pt-BR).
- **Uso dos dados**: todos os arquivos fornecidos serão usados — CSVs de produtos, categorias, pedidos, itens de pedido, clientes, promoções e o PDF de políticas (o desafio permite não usar tudo, mas a cobertura completa maximiza a experiência).
- **Identificação do cliente**: feita na conversa por nome completo ou e-mail, sem autenticação forte — aceitável para protótipo.
- **Histórico de conversa**: persistido em SQLite (checkpoints por thread) desde a v1, por decisão do autor — conversas sobrevivem a restart do processo; retenção é ilimitada no protótipo e essa limitação será documentada no README (entra no "o que faria com mais tempo").
- **Canal**: a integração real com WhatsApp está fora de escopo — a UI web escolhida simula o chat de atendimento.
- **Chave da API**: será gerada uma chave OpenAI dedicada, compartilhada por e-mail com o avaliador junto ao link do repositório; a chave nunca será commitada — a UI provisiona o `.env` local no primeiro acesso.
- **Prazo de entrega**: definido no e-mail do processo seletivo (não consta no artefato); o repositório não será alterado após o prazo, conforme exigido.
- **Horário de atendimento do agente**: o agente responde a qualquer hora; quando a pergunta depender de ação humana, informa o horário de funcionamento/retorno conforme o manual.
