<!--
SYNC IMPACT REPORT (temporário — remover antes de commitar)
- Mudança de versão: (não ratificada — template com placeholders) -> 1.0.0 (primeira ratificação)
- Princípios modificados: IV. Arquitetura Limpa (exemplos de I/O generalizados, sem nomear tools)
- Princípios adicionados: I. Evidência ou Nada; II. Test-First; III. Simplicidade Radical;
  IV. Arquitetura Limpa e Clean Code; V. Conhecimento Vivo; VI. Código sem Ruído;
  VII. Clareza antes de Código
- Seções adicionadas: "Restrição Técnica e Escolhas Justificadas" (reframada: era "Stack e
  Restrições Técnicas" que congelava stack — corrigido para alinhar ao enunciado do desafio,
  cuja única restrição obrigatória é Python; demais escolhas são ADR/README, não constituição);
  "Fluxo de Trabalho e Gates de Qualidade"; Governance preenchida
- Seções removidas: nenhuma
- Follow-ups: criar docs/adrs/ e docs/learning-lessons/ durante a implementação da feature 001;
  o primeiro ADR candidate é a decisão D2 (single container in-process vs LangGraph Server);
  provisão dos agentes de pesquisa fica a cargo do mantenedor do projeto
-->
# Q&A Agent (Empório da Música) Constitution

## Core Principles

### I. Evidência ou Nada

Nenhuma afirmação técnica é feita sem evidência verificável: código lido, documentação oficial
consultada, teste executado ou fonte citada. A documentação oficial é o PADRÃO-OURO: é proibido
assumir comportamento de biblioteca, API ou versão sem lê-la no estado atual. Para o ecossistema
LangChain, a consulta DEVE passar pelo context7 (ou fonte oficial equivalente) antes de codificar,
pois versões mudam rápido. Se uma fonte falhar, o erro da fonte é reportado — nunca se inventa
valor, versão ou comportamento. Pesquisa web é obrigatória quando a evidência local não resolve.

### II. Test-First (NON-NEGOTIABLE)

TDD é obrigatório em todo código de produção: o teste é escrito primeiro, DEVE falhar pelo motivo
certo, e só então a implementação mínima é escrita (Red-Green-Refactor). Neste projeto isso se
concretiza em três camadas: testes unitários (ingestão e tools, SQL determinístico), testes de
integração (fluxo agente -> tools -> fontes) e bateria de eval (perguntas-ouro do quickstart
contra o agente real). Código sem teste prévio NÃO é mergeável.

### III. Simplicidade Radical

A implementação escolhida é sempre a mais simples que atende aos requisitos comprovados (KISS,
YAGNI). Número mínimo de serviços, processos e conceitos; qualquer complexidade adicional DEVE ser
justificada por escrito (na spec, no plano ou em ADR) com a alternativa simples rejeitada e o
motivo da rejeição. Código existente é continuamente simplificado quando tocado.

### IV. Arquitetura Limpa e Clean Code

O código segue Arquitetura Limpa: regras de domínio no centro, independentes de framework, LLM,
UI e banco; I/O (modelo, interface, vetores, banco, arquivos) fica nas bordas atrás de interfaces.
Padrões de projeto consagrados são usados quando resolvem um problema real — nunca por vaidade.
Nomes revelam intenção; funções são pequenas e de propósito único; efeitos colaterais são
explícitos. Clean Code é requisito de revisão, não sugestão.

### V. Conhecimento Vivo

Decisões arquiteturais materiais geram ADR em `docs/adrs/` na mesma entrega que as introduz.
Erros, pegadinhas e achados viram learning lesson em `docs/learning-lessons/`. Investigações
não triviais são apoiadas por agentes de pesquisa (exploração de codebase, web, docs) antes de
decidir. O conhecimento registrado é lido antes de refazer uma decisão já tomada.

### VI. Código sem Ruído

É proibido o uso de emojis em código, documentação e mensagens de commit. Comentários só quando
indispensáveis: explicam o PORQUÊ não óbvio, nunca o que o código já diz. Arquivos NÃO têm
docstring de cabeçalho. Funções carregam docstring detalhada; nas tools do agente ela é
OBRIGATÓRIA e completa (propósito, argumentos, retorno, erros), pois é o contrato que o LLM lê
para decidir quando e como chamá-las.

### VII. Clareza antes de Código

Diante de ambiguidade material de escopo, requisito ou decisão técnica com múltiplas leituras
razoáveis, a ação obrigatória é PERGUNTAR e aguardar esclarecimento. Só se assume uma
interpretação quando a pergunta é inviável — e nesse caso a suposição é documentada (spec/README)
antes de prosseguir, alinhado à própria orientação do desafio.

## Restrição Técnica e Escolhas Justificadas

- Única restrição técnica obrigatória, definida pelo enunciado do desafio: Python como linguagem
  principal. Tudo o mais é escolha, não restrição.
- Todas as demais decisões técnicas — framework/abordagem do agente, modelo e provedor,
  interface de interação, persistência do histórico, estratégia de retrieval, tratamento dos
  dados — são decisões a critério do autor, justificadas no README (exigência explícita do
  desafio) e registradas como ADR quando arquiteturais (Princípio V). A constituição NÃO congela
  stack: a stack candidata atual vive em `research.md` e ADRs, não aqui; mudá-la é reescrever um
  ADR, não emendar a governança.
- O agente é mínimo por design (Princípio III): um único processo com o menor conjunto de tools
  e serviços que cumpre a spec; maturidade se demonstra escolhendo o ecossistema adequado e
  sabendo excluir o que não é necessário — não somando serviços.
- Versões das bibliotecas são apuradas no context7/documentação oficial no momento da
  implementação e pinadas no `pyproject.toml` (Princípio I).
- Configuração exclusivamente via variáveis de ambiente; segredos nunca são commitados.

## Fluxo de Trabalho e Gates de Qualidade

1. Pesquisa na documentação oficial (context7) e exploração da codebase antes de qualquer código.
2. Decisão material registrada (ADR) quando arquitetural.
3. TDD: teste que falha -> implementação mínima -> refactor com testes verdes.
4. Execução da bateria de validação do `quickstart.md` da feature em curso.
5. Revisão verifica: conformidade com esta constituição, simplicidade, ausência de ruído
   (Princípio VI) e cobertura de testes.
- O Constitution Check de `/speckit-plan` DEVE avaliar cada princípio e recusar planos que violem
  gates sem justificativa documentada.

## Governance

- Esta constituição prevalece sobre qualquer prática conflitante do projeto.
- Emendas exigem proposta documentada (o quê, por quê, impacto), aprovação explícita do
  mantenedor e, quando aplicável, plano de migração do código/processos afetados.
- Versionamento semântico: MAJOR para remoção/redefinição incompatível de princípios; MINOR para
  novo princípio/seção ou expansão material; PATCH para esclarecimentos e correções sem mudança
  de significado.
- Revisão de conformidade ocorre em todo `/speckit-plan` (Constitution Check), em revisões de
  código e antes de releases.
- O Sync Impact Report no topo deste arquivo é material temporário de revisão e DEVE ser removido
  antes do commit da emenda.

**Version**: 1.0.0 | **Ratified**: 2026-11-03 | **Last Amended**: 2026-11-03
