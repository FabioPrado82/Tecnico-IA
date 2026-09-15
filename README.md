# Técnico com IA — Save FC (backend)

Fundação do backend: FastAPI + PostgreSQL, com o fluxo pré-jogo já
funcionando de ponta a ponta (testado neste ambiente).

## O que já está pronto

- **Banco de dados**: schema completo (26 tabelas) aplicado a partir de
  `schema.sql` — já inclui todas as tabelas de tempo real, pós-jogo,
  pênaltis, voz e divulgação, mesmo que a API ainda não exponha todas.
- **Autenticação**: JWT + bcrypt. Comissão e auxiliar compartilham o mesmo
  login com acesso completo (decisão já registrada no planejamento — sem
  papel restrito por enquanto). Todo endpoint interno exige token; só o
  link público de confirmação do atleta (`/confirmar/{token}`) fica aberto.
- **Frontend do auxiliar (funcional, não mockup)**: `static/auxiliar.html`,
  servido pelo próprio backend em `/app/auxiliar.html`. Login, cronômetro,
  registro de eventos (com o fluxo condicional time/jogador), e conexão
  WebSocket ao vivo — quando um gatilho dispara, o modal abre sozinho na
  tela, sem o auxiliar precisar fazer nada. Testado com navegador real
  (Playwright/Chromium) neste ambiente: login → tela do jogo → WebSocket
  conecta → gol registrado → modal do gatilho abre sozinho via WebSocket →
  resposta enviada → erro da IA (sem chave) aparece de forma clara no modal.
  Também cobre: ajuste manual do cronômetro (com auditoria em
  `ajustes_cronometro`) e contador de substituições (incrementado
  automaticamente ao registrar o evento, editável manualmente com limite
  travado em `substituicoes_permitidas`).
- **Tempo real via WebSocket**: `GET /ws/partidas/{id}?token=...` — conexão que
  o auxiliar mantém aberta durante o jogo. Toda vez que um gatilho é criado
  (gol/cartão), um ciclo regular é gerado, ou uma sugestão fica pronta, a
  mensagem chega automaticamente por essa conexão — sem precisar de polling.
  O token vai na query string porque o WebSocket nativo do navegador não
  suporta header `Authorization` customizado. Testado ponta a ponta neste
  ambiente (gatilho chegando em menos de 1s após o evento ser registrado via
  REST, token inválido rejeitado, e nenhum broadcast disparado quando a
  chamada à IA falha antes de gerar a sugestão).
- **Integração com a IA — todos os 8 modos plugados**: `app/core/ai_client.py`
  centraliza a chamada à API da Claude (persona base + instrução do modo +
  contexto, espera JSON de volta). Sem `ANTHROPIC_API_KEY` configurada,
  qualquer um dos 8 endpoints abaixo devolve `503` com mensagem clara em vez
  de travar — testado ponta a ponta neste ambiente.

  | Modo | Endpoint | O que faz |
  |---|---|---|
  | 1 — Scouting dinâmico | `POST /partidas/{id}/scouting/gerar-dinamicas` | Gera perguntas específicas do confronto |
  | 2 — Ciclo regular | `POST /partidas/{id}/ciclos/gerar-pergunta` | Pergunta de múltipla escolha a cada 2-3min |
  | 3 — Sugestão | `PATCH /ciclos/{id}/responder` | Sugestão tática após resposta do ciclo/gatilho |
  | 4 — Gatilho | `POST /partidas/{id}/eventos` | Templates fixos (sem IA) — só a sugestão depois usa o Modo 3 |
  | 5 — Retrospecto | `POST /partidas/{id}/retrospecto/gerar` | Cruza scouting pré-jogo com o que aconteceu |
  | 6 — Chat livre | `POST /chat/mensagens` | Conversa livre com o assistente |
  | 7 — Pênaltis | `POST /partidas/{id}/penaltis/sugestao-ordem` | Ordem de batedores (aproveitamento calculado pela aplicação) |
  | 8 — Voz | `POST /partidas/{id}/voz/interpretar` | Interpreta transcrição em evento/resposta estruturada |

- **Avaliação em lote por link público**: mesmo padrão do link de
  confirmação de presença — a comissão gera um link (autenticado), o técnico
  responde sem login, avaliando quantos atletas quiser por vez (envios
  parciais são permitidos; só fecha quando `finalizar=true`).
- **API**:
  - `POST /auth/usuarios` — cadastra um membro da comissão
  - `POST /auth/login` — login (e-mail + senha), devolve o token JWT
  - `GET /auth/me` — dados do usuário autenticado
  - `POST /atletas`, `GET /atletas` — cadastro de elenco (autenticado)
  - `POST /partidas` — cria a partida **e já gera automaticamente** uma
    linha de convocação (com link_token único) pra cada atleta ativo
  - `GET /partidas/{id}/convocacao` — painel de acompanhamento da comissão
  - `GET/POST /confirmar/{token}` — página pública que o atleta usa pra
    confirmar presença (sem login), já validando que o link expira quando
    a partida é finalizada
  - `POST /partidas/{id}/scouting/inicializar` — cria as 11 perguntas fixas
    de scouting pra essa partida (idempotente — não duplica se já existir)
  - `GET /partidas/{id}/scouting` — lista perguntas fixas + dinâmicas
  - `POST /partidas/{id}/scouting/gerar-dinamicas` — Modo 1 de verdade: chama
    a IA e já salva as perguntas geradas (idempotente)
  - `PATCH /scouting/{id}/responder` — comissão responde uma pergunta
  - `GET /adversarios/{id}/comentarios` — histórico de comentários entre
    confrontos
  - `POST /partidas/{id}/comentarios-adversario` — novo comentário livre
  - `POST /avaliacoes/sessoes` — gera o link de avaliação em lote (autenticado,
    feito pela comissão)
  - `GET/POST /avaliar/{token}` — página pública que o técnico usa pra
    avaliar o elenco (sem login), cobrindo todos os atletas ativos no
    momento da criação do link

## Como rodar localmente

```bash
# 1. Banco de dados
createdb tecnico_ia
psql -d tecnico_ia -f schema.sql

# 2. Dependências
pip install -r requirements.txt

# 3. Variáveis de ambiente (ajuste usuário/senha/host conforme seu ambiente)
export DATABASE_URL="postgresql://usuario:senha@localhost:5432/tecnico_ia"
export SECRET_KEY="troque-por-uma-chave-secreta-forte-em-producao"

# 4. Subir o servidor
uvicorn app.main:app --reload
```

A API sobe em `http://localhost:8000`. Documentação interativa automática
em `http://localhost:8000/docs`.

## Estrutura

```
app/
  core/
    config.py       # configuração (variáveis de ambiente)
    database.py     # conexão SQLAlchemy
  models/
    core.py         # Clube, Atleta, Campeonato, Adversario
    partida.py       # Partida, Convocacao
  schemas/
    core.py         # validação de entrada/saída da API (Pydantic)
  routers/
    atletas.py
    partidas.py
    confirmacao.py   # endpoint público do link do atleta
  main.py            # ponto de entrada
```

## Simplificações desta versão (documentadas no próprio código)

- **Pênaltis**: usa `convocacao.titular = true` como proxy de "quem está em
  campo" no momento da disputa — ainda não rastreamos substituições em tempo
  real o suficiente pra saber a escalação exata nesse momento específico.
- **WebSocket sem reconexão automática no código de exemplo**: o servidor
  aceita reconexões normalmente, mas o cliente (frontend) precisa implementar
  a lógica de reconectar se a conexão cair — isso ainda não está desenhado.
- **`ordem_final` do Modo 7**: guarda sugestão e ordem final lado a lado, mas
  ainda não existe endpoint que analise a correlação entre seguir a IA e o
  resultado — fica pra quando houver dado real acumulado.

- **Frontend do auxiliar completo**: cobre todos os eventos principais (gol,
  cartão, falta, escanteio, substituição com os dois campos), cronômetro com
  ajuste manual, contador de substituições, **chat livre com o assistente**,
  e **pênaltis** (gerar sugestão de ordem, reordenar manualmente, confirmar
  ordem final, e registrar cada cobrança em tempo real — nosso e do
  adversário, com a numeração recarregada corretamente do banco em caso de
  reload no meio da disputa). Testado ponta a ponta com navegador real
  neste ambiente, incluindo o cenário de reload.
- **Página pública do atleta** (`static/confirmar.html`, servida em
  `/app/confirmar.html?token=...`): mostra nome do adversário, fase, data,
  vestiário e local; fluxo Vou/Não vou; ao reabrir depois de já ter
  respondido, mostra a confirmação em vez de deixar responder de novo.
  Testado com navegador real, incluindo o cenário de reabertura.
- **Painel da comissão** (`static/comissao.html`, em `/app/comissao.html`):
  login, convocação com nomes reais e status (confirmado/pendente/recusado),
  scouting (inicializar perguntas fixas, gerar dinâmicas via IA, responder
  múltipla escolha e texto livre), e retrospecto (gerar, editar, aprovar).
  Testado ponta a ponta neste ambiente.
- **Painel da comissão completo**: login (sem precisar mais digitar ID de
  partida manualmente), tela de partidas (lista as existentes com nome do
  adversário, cria campeonato/adversário/partida novos direto pela tela — a
  convocação é gerada automaticamente pros atletas ativos), convocação com
  nomes reais, scouting (fixo + dinâmico via IA), e retrospecto. Testado
  ponta a ponta neste ambiente, incluindo o fluxo completo de criar tudo do
  zero (campeonato → adversário → partida → convocação automática).
- **Arte de divulgação real** (`static/arte.html`, em `/app/arte.html`):
  renderização por canvas (template fixo, sem IA de imagem — como decidido),
  com escudo do clube (cor real via `clubes.cor_primaria`), escudo do
  adversário, alternância pré/pós-jogo, jogadores em destaque (até 3),
  patrocinadores (respeitando `clubes.limite_patrocinadores`, com criação
  direto pela tela), e frase pré-preenchida com `clubes.slogan`. O botão
  "Baixar PNG" gera o arquivo de verdade no navegador. Testado ponta a
  ponta neste ambiente, incluindo o download real do arquivo (56KB,
  conteúdo verificado, não em branco).
- **Interface de voz no auxiliar**: botão de microfone usa o reconhecimento
  de fala nativo do navegador (Web Speech API, sem custo), manda a
  transcrição pro Modo 8 interpretar, e sempre mostra um painel de
  confirmação antes de registrar qualquer coisa — nunca comita direto,
  como decidido no planejamento. As sugestões da IA (tanto por ciclo quanto
  por WebSocket) agora são lidas em voz alta automaticamente (texto-pra-fala
  nativo). Testado com dois cenários: erro da IA tratado corretamente (sem
  chave) e o caminho de sucesso completo simulado via interceptação de
  rede — interpretação aparece, confirmação registra o evento certo no
  backend (testado que o corpo enviado tem tipo/time/atleta corretos).
- **Nenhuma lacuna de fluxo conhecida no MVP de futebol/tática** — pré-jogo,
  tempo real e pós-jogo têm tela real de ponta a ponta.
- **Finalização de partida com retrospecto automático**:
  `PATCH /partidas/{id}/finalizar` — fecha a partida (placar, status,
  período) e já chama o Modo 5 automaticamente. A finalização **nunca falha
  por causa da IA** — se a geração do retrospecto der erro (ex: sem chave),
  a partida mesmo assim fica finalizada, e a resposta informa
  `retrospecto_gerado: false` com o motivo. Bloqueia finalizar a mesma
  partida duas vezes (`400`). Confirmado também que o link do atleta passa
  a responder `410` assim que a partida finaliza de verdade (regra que já
  existia, agora testada ponta a ponta com uma finalização real).

## Todos os 8 modos de IA validados com chave real

Testado ponta a ponta neste ambiente com uma chave de API real (já revogada
depois do teste). Três bugs reais só apareceram nesse processo, todos
corrigidos:

1. **Header `anthropic-workspace-id` ausente** — chaves não vinculadas a um
   workspace específico exigem esse header em toda chamada. Adicionado como
   configuração opcional (`ANTHROPIC_WORKSPACE_ID` no `.env`) em
   `app/core/ai_client.py`.
2. **Parsing assumia bloco de texto no índice 0** — com "extended thinking"
   habilitado, o primeiro bloco de resposta pode ser um `ThinkingBlock`, não
   texto. Corrigido pra buscar o bloco certo pelo `type`.
3. **`max_tokens` baixo demais** nos Modos 3 e 8, cortando a resposta da IA
   no meio do JSON. Aumentado com margem de segurança.

Resultados observados nos testes reais (com dado genuíno, não simulado):
- **Modo 1**: gerou pergunta referenciando "zona 6 nos escanteios" —
  puxando um comentário histórico real cadastrado numa sessão anterior
- **Modo 3**: sugestão corretamente mencionou "sem trocas disponíveis",
  batendo com o estado real de substituições da partida no banco
- **Modo 5**: retrospecto identificou corretamente perguntas de gatilho sem
  resposta e falta de detalhe no scouting, virando lições práticas
- **Modo 7**: honesto sobre falta de histórico de pênaltis, sem inventar
  aproveitamento
- **Modo 8**: identificou "bruno" corretamente como Bruno Lima entre os
  jogadores em campo

## Endpoints novos nesta rodada

- `PATCH /partidas/{id}/finalizar` — fecha a partida e dispara o retrospecto

## Endpoints de rodadas anteriores

- `GET /clubes/{id}` — dados do clube (cores, slogan, limite de patrocinadores)
- `POST/GET /patrocinadores` — criar e listar patrocinadores por clube
- `POST/GET /partidas/{id}/artes-divulgacao` — registrar/listar metadados de
  cada arte gerada (a imagem em si não é enviada ao servidor, só o registro
  de quando/como foi montada)
- `POST/GET /campeonatos` — criar e listar campeonatos por clube
- `POST/GET /adversarios` — criar e listar adversários (lista global, sem
  vínculo com clube — mesmo adversário pode aparecer em confrontos de
  qualquer clube que usar o sistema)

## Próximos passos naturais

1. Importação do Excel de avaliação de atletas (aguardando arquivo preenchido)
