# Contract: Fluxos da UI (Gradio)

## F0 — Onboarding da chave (primeiro acesso / chave ausente ou inválida)

1. App sobe e detecta `OPENAI_API_KEY` ausente/inválida (validação barata contra a API).
2. Exibe tela de configuração: campo de texto (password) + botão "Salvar e começar".
3. Ao salvar: grava `.env` local, recarrega settings, valida a chave com uma chamada mínima.
4. Sucesso → entra no chat (F1). Falha → mensagem de erro clara, permanece na tela.
5. `.env` permanece apenas local (`.gitignore`); a chave nunca aparece em logs nem em mensagens do chat.

## F1 — Chat de atendimento

- Interface de conversa com streaming token a token.
- Cada chamada de tool aparece como bloco recolhível "Consultando catálogo/políticas/pedidos…" (metadata do Gradio) — demonstra explicitamente a decisão dados-vs-políticas exigida pelo desafio.
- Botão "Nova conversa" → novo `thread_id` (checkpoint anterior permanece no SQLite).
- Mensagens de erro do runtime (provider indisponível, rate limit) → mensagem amigável em pt-BR + orientação (tentar novamente / verificar chave).

## F2 — Comportamento fora do expediente

- O agente informa horários quando perguntado (via políticas), mas funciona 24×7 (assistente virtual); se o cliente precisar de ação humana, a resposta inclui horário de retorno e canais.

## Fora de escopo da UI (v1)

- Multiusuário com login, upload de arquivos, voz/áudio, histórico visual de conversas anteriores (existe no SQLite, sem tela de listagem).
