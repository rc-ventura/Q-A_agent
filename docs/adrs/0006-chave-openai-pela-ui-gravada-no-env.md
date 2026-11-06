# ADR-0006: Chave da OpenAI configurada pela UI e gravada no `.env` local

## Status
Aceito (2026-11-05). Formaliza as decisões D5 e D6 do `research.md` e o FR-016 da spec.

## Contexto
O avaliador recebe uma chave dedicada por e-mail e precisa rodar o projeto em menos de 15 minutos
(SC-006). Editar arquivos de configuração é a etapa mais propensa a erro desse fluxo (nome da
variável, aspas, espaços, arquivo no lugar errado). Alternativas consideradas:

- Exigir `cp .env.example .env` e edição manual: simples de implementar, mas falha silenciosa quando a
  chave tem espaço ou quebra de linha, e o erro só aparece na primeira pergunta.
- Variável de ambiente no `docker compose`: obriga o avaliador a exportar a chave no shell, e ela vai
  parar no histórico do terminal.
- Tela de configuração no próprio app: a chave é colada uma vez, validada na hora e persistida.

## Decisão
Sem chave válida, o app abre numa tela de configuração com campo de senha. Ao confirmar:

1. a chave é validada com `models.list()` na OpenAI, distinguindo chave recusada de falha de rede;
2. só então é gravada no `.env` local (`save_api_key`): rejeita espaços e quebras de linha (evita
   injetar linhas no arquivo), preserva as outras variáveis e aplica permissão `0600`;
3. os dados são preparados (ingestão e índice) e o chat é liberado.

A chave é `SecretStr` nas configurações, não aparece em logs nem em mensagens de erro (os erros
mostram só a categoria), e o `.env` está no `.gitignore` e no `.dockerignore`.

## Consequências
- Positivas: um comando e uma colagem levam ao chat; chave errada é rejeitada antes de gravar, com
  mensagem em português; a mesma tela serve para trocar a chave.
- Negativas: não há controle de acesso à tela nem ao endpoint `/submit_key` do Gradio: quem alcança a
  porta 7860 pode trocar a chave. No Docker, o `.env` gravado pela tela vive no sistema de arquivos do
  container e se perde com `docker compose down`.
- Neutras: aceitável para avaliação local ou demonstração; em rede aberta exigiria autenticação e um
  cofre de segredos, registrados como limitação no README.
