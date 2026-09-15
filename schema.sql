-- =========================================================
-- Técnico com IA — Save FC
-- Modelo de dados MVP (PostgreSQL)
-- =========================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- necessária para gen_random_uuid()

-- 1. CLUBES (hoje só o Save, estrutura já pronta para múltiplos times no futuro)
CREATE TABLE clubes (
    id                       SERIAL PRIMARY KEY,
    nome                     VARCHAR(120) NOT NULL,
    logo_url                 VARCHAR(255),
    cor_primaria             VARCHAR(7),   -- hex, usada nos templates de arte de divulgação
    cor_secundaria           VARCHAR(7),
    limite_patrocinadores    SMALLINT NOT NULL DEFAULT 5,  -- 5 ou 10, conforme plano contratado
    slogan                   VARCHAR(150)   -- frase padrão do clube, sugerida por padrão na arte de divulgação
);

-- 1B. USUÁRIOS (login da comissão — auxiliar usa o mesmo acesso, sem papel restrito)
CREATE TABLE usuarios (
    id         SERIAL PRIMARY KEY,
    clube_id   INTEGER NOT NULL REFERENCES clubes(id),
    nome       VARCHAR(120) NOT NULL,
    email      VARCHAR(150) NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    ativo      BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. ATLETAS ---------------------------------------------------
CREATE TABLE atletas (
    id                   SERIAL PRIMARY KEY,
    clube_id             INTEGER NOT NULL REFERENCES clubes(id),
    nome                 VARCHAR(120) NOT NULL,
    apelido              VARCHAR(60),
    cpf                  VARCHAR(14),  -- dado sensível (LGPD) — considerar acesso restrito/criptografia em produção
    data_nascimento      DATE,
    posicao_principal    VARCHAR(30),  -- pode ser preenchida depois, junto com a avaliação técnica
    posicoes_secundarias VARCHAR(30)[] DEFAULT '{}',
    pe_dominante         VARCHAR(10) CHECK (pe_dominante IN ('destro','canhoto','ambidestro')),
    altura_cm            SMALLINT,
    peso_kg              NUMERIC(5,2),
    ativo                BOOLEAN NOT NULL DEFAULT TRUE,
    foto_url             VARCHAR(255),
    criado_em            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. AVALIAÇÕES TÉCNICAS/TÁTICAS (histórico — permite reavaliar ao longo do tempo)
CREATE TABLE avaliacoes_atleta (
    id              SERIAL PRIMARY KEY,
    atleta_id       INTEGER NOT NULL REFERENCES atletas(id),
    data_avaliacao  DATE NOT NULL DEFAULT CURRENT_DATE,
    -- técnico (escala 1-5)
    passe           SMALLINT CHECK (passe BETWEEN 1 AND 5),
    finalizacao     SMALLINT CHECK (finalizacao BETWEEN 1 AND 5),
    drible          SMALLINT CHECK (drible BETWEEN 1 AND 5),
    cabeceio        SMALLINT CHECK (cabeceio BETWEEN 1 AND 5),
    desarme         SMALLINT CHECK (desarme BETWEEN 1 AND 5),
    cruzamento      SMALLINT CHECK (cruzamento BETWEEN 1 AND 5),
    controle_bola   SMALLINT CHECK (controle_bola BETWEEN 1 AND 5),
    -- tático (escala 1-5)
    visao_jogo      SMALLINT CHECK (visao_jogo BETWEEN 1 AND 5),
    posicionamento  SMALLINT CHECK (posicionamento BETWEEN 1 AND 5),
    marcacao        SMALLINT CHECK (marcacao BETWEEN 1 AND 5),
    lideranca       SMALLINT CHECK (lideranca BETWEEN 1 AND 5),
    versatilidade   SMALLINT CHECK (versatilidade BETWEEN 1 AND 5),
    -- pênaltis (escala 1-5) — classificação inicial dada pela comissão, usada pela IA
    -- como base enquanto não houver histórico real suficiente em penaltis_cobranca
    cobranca_penalti SMALLINT CHECK (cobranca_penalti BETWEEN 1 AND 5),
    defesa_penalti   SMALLINT CHECK (defesa_penalti BETWEEN 1 AND 5),  -- relevante para goleiros
    avaliado_por    VARCHAR(120),
    observacoes     TEXT
);

-- 4. CONDIÇÃO FÍSICA / LESÕES (histórico de status)
CREATE TABLE condicao_fisica (
    id               SERIAL PRIMARY KEY,
    atleta_id        INTEGER NOT NULL REFERENCES atletas(id),
    data             DATE NOT NULL DEFAULT CURRENT_DATE,
    status           VARCHAR(20) NOT NULL CHECK (status IN ('apto','em_recuperacao','lesionado','suspenso')),
    tipo_lesao       VARCHAR(120),
    previsao_retorno DATE,
    observacoes      TEXT
);

-- 5. CAMPEONATOS -------------------------------------------------
-- Um clube pode estar em vários campeonatos ao mesmo tempo (cada linha é independente)
CREATE TABLE campeonatos (
    id              SERIAL PRIMARY KEY,
    clube_id        INTEGER NOT NULL REFERENCES clubes(id),
    nome            VARCHAR(120) NOT NULL,
    temporada       VARCHAR(20),
    fase_atual      VARCHAR(50),      -- ex: fase de grupos, mata-mata, semifinal
    status          VARCHAR(20) NOT NULL DEFAULT 'em_andamento'
                    CHECK (status IN ('em_andamento','finalizado')),
    posicao_tabela  SMALLINT,
    pontos          SMALLINT,
    jogos_restantes SMALLINT
);

-- 6. DOCUMENTOS DO CAMPEONATO (tabela de classificação, regulamento — com histórico de versões)
CREATE TABLE campeonato_documentos (
    id            SERIAL PRIMARY KEY,
    campeonato_id INTEGER NOT NULL REFERENCES campeonatos(id),
    tipo          VARCHAR(20) NOT NULL CHECK (tipo IN ('tabela','regulamento')),
    arquivo_url   VARCHAR(255) NOT NULL,
    enviado_em    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 7. ADVERSÁRIOS (mestre — permite histórico entre confrontos ao longo do tempo)
CREATE TABLE adversarios (
    id       SERIAL PRIMARY KEY,
    nome     VARCHAR(120) NOT NULL UNIQUE,
    logo_url VARCHAR(255)
);

-- 8. PARTIDAS ------------------------------------------------------
CREATE TABLE partidas (
    id                        SERIAL PRIMARY KEY,
    clube_id                  INTEGER NOT NULL REFERENCES clubes(id),
    campeonato_id             INTEGER NOT NULL REFERENCES campeonatos(id),
    adversario_id             INTEGER NOT NULL REFERENCES adversarios(id),
    fase                      VARCHAR(50),   -- ex: primeira fase, oitavas, quartas, semifinal, final
    data_hora                 TIMESTAMPTZ NOT NULL,
    horario_chegada_vestiario TIMESTAMPTZ,
    duracao_tempo_min         SMALLINT NOT NULL DEFAULT 45,  -- duração de cada tempo (varia por campeonato)
    quantidade_tempos         SMALLINT NOT NULL DEFAULT 2,
    tem_prorrogacao           BOOLEAN NOT NULL DEFAULT FALSE,   -- definido na criação (mata-mata costuma ter)
    duracao_prorrogacao_min   SMALLINT DEFAULT 15,
    periodo_atual             VARCHAR(20) NOT NULL DEFAULT '1_tempo'
                              CHECK (periodo_atual IN ('1_tempo','intervalo','2_tempo','prorrogacao','penaltis','finalizado')),
    substituicoes_permitidas  SMALLINT NOT NULL DEFAULT 5,  -- varia por regulamento do campeonato
    substituicoes_realizadas  SMALLINT NOT NULL DEFAULT 0,  -- controlado e editável pelo auxiliar em tempo real
    local                     VARCHAR(10) CHECK (local IN ('casa','fora')),
    local_nome                VARCHAR(150),  -- nome/endereço do campo, ex: "Campo do Bairro" (usado no banner e no link do atleta)
    status                    VARCHAR(20) NOT NULL DEFAULT 'agendada'
                              CHECK (status IN ('agendada','em_andamento','finalizada')),
    placar_nosso       SMALLINT,
    placar_adversario  SMALLINT
);

-- 9. CONDIÇÕES DA PARTIDA (clima e outros fatores ambientais — data/horário já em `partidas.data_hora`)
CREATE TABLE condicoes_partida (
    id                  SERIAL PRIMARY KEY,
    partida_id          INTEGER NOT NULL UNIQUE REFERENCES partidas(id),
    temperatura_c       NUMERIC(4,1),
    condicao_climatica  VARCHAR(30),   -- ex: sol, nublado, chuva, chuva_forte
    umidade_pct         SMALLINT,
    tipo_gramado        VARCHAR(20) CHECK (tipo_gramado IN ('natural','sintetico','misto')),
    horario_confirmado  TIMESTAMPTZ,   -- caso o horário mude em relação ao agendado em `partidas`
    observacoes         TEXT,          -- outros fatores relevantes (vento forte, jogo remarcado, etc.)
    registrado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 10. CONVOCAÇÃO / DISPONIBILIDADE (o filtro de 30 -> 18)
-- Três momentos de captura: (1) atleta responde o link — presença + se já tem outro jogo antes;
-- (2) staff confirma o desgaste real na chegada ao estádio; (3) comissão decide titulares/reservas.
CREATE TABLE convocacao (
    id                        SERIAL PRIMARY KEY,
    partida_id                INTEGER NOT NULL REFERENCES partidas(id),
    atleta_id                 INTEGER NOT NULL REFERENCES atletas(id),
    disponivel                BOOLEAN NOT NULL DEFAULT TRUE,
    motivo_indisponibilidade  VARCHAR(120),
    convocado                 BOOLEAN NOT NULL DEFAULT FALSE,
    titular                   BOOLEAN NOT NULL DEFAULT FALSE,

    -- confirmação de presença via link enviado no WhatsApp
    link_token                UUID NOT NULL DEFAULT gen_random_uuid(),
    link_enviado_em           TIMESTAMPTZ,
    lembrete_enviado_em       TIMESTAMPTZ,       -- último lembrete automático disparado
    quantidade_lembretes      SMALLINT NOT NULL DEFAULT 0,
    presenca_confirmada       VARCHAR(10) NOT NULL DEFAULT 'pendente'
                              CHECK (presenca_confirmada IN ('pendente','confirmado','recusado')),
    presenca_respondida_em    TIMESTAMPTZ,

    -- respondido pelo próprio atleta junto da confirmação (estimativa inicial de desgaste)
    jogos_antes_desta_partida SMALLINT CHECK (jogos_antes_desta_partida BETWEEN 0 AND 3),
                              -- 0 = nenhum, 1, 2, 3 = "3 ou mais"

    -- confirmação real, feita minutos antes do jogo pelo staff (ou durante, se mudar)
    jogos_previos_confirmado  SMALLINT,
    jogou_em_confirmado       TIMESTAMPTZ,      -- data/hora do último jogo antes deste
    nivel_desgaste_confirmado VARCHAR(10) CHECK (nivel_desgaste_confirmado IN ('baixo','medio','alto')),
    confirmado_por            VARCHAR(120),
    confirmado_em             TIMESTAMPTZ,      -- quando essa confirmação foi registrada

    UNIQUE (partida_id, atleta_id)
);

-- 11. SCOUTING DO ADVERSÁRIO (perguntas fixas + dinâmicas, por partida)
CREATE TABLE scouting_adversario (
    id             SERIAL PRIMARY KEY,
    partida_id     INTEGER NOT NULL REFERENCES partidas(id),
    tipo_pergunta  VARCHAR(10) NOT NULL CHECK (tipo_pergunta IN ('fixa','dinamica')),
    pergunta       TEXT NOT NULL,
    tipo_resposta  VARCHAR(20) NOT NULL DEFAULT 'texto'
                   CHECK (tipo_resposta IN ('texto','multipla_escolha')),
    opcoes         VARCHAR(60)[],   -- preenchido só quando tipo_resposta = multipla_escolha
    resposta       TEXT,            -- texto livre OU a opção escolhida
    respondido_por VARCHAR(120),
    respondido_em  TIMESTAMPTZ
);

-- 12. COMENTÁRIOS LIVRES SOBRE O ADVERSÁRIO (acumula histórico entre confrontos)
-- origem = 'ia_pos_jogo' quando criado automaticamente pelo retrospecto ao finalizar a partida
CREATE TABLE comentarios_adversario (
    id            SERIAL PRIMARY KEY,
    adversario_id INTEGER NOT NULL REFERENCES adversarios(id),
    partida_id    INTEGER REFERENCES partidas(id),   -- opcional, se ligado a um jogo específico
    origem        VARCHAR(15) NOT NULL DEFAULT 'comissao'
                  CHECK (origem IN ('comissao','ia_pos_jogo')),
    comentario    TEXT NOT NULL,
    autor         VARCHAR(120),
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 13. EVENTOS DA PARTIDA (feed em tempo real, alimentado pelo auxiliar)
CREATE TABLE eventos_partida (
    id                  SERIAL PRIMARY KEY,
    partida_id          INTEGER NOT NULL REFERENCES partidas(id),
    time                VARCHAR(10) NOT NULL DEFAULT 'nosso' CHECK (time IN ('nosso','adversario')),
    atleta_id           INTEGER REFERENCES atletas(id),        -- quem fez/sofreu o evento (time = nosso); em substituição, quem saiu
    atleta_entrou_id    INTEGER REFERENCES atletas(id),        -- só em substituição: quem entrou
    assistente_id       INTEGER REFERENCES atletas(id),        -- só em gol nosso, quando houver assistência
    jogador_adversario  VARCHAR(120),                          -- nome/número do jogador adversário, se souber (time = adversario)
    minuto              SMALLINT NOT NULL,
    tipo_evento         VARCHAR(30) NOT NULL CHECK (tipo_evento IN (
                            'gol','cartao_amarelo','cartao_vermelho','falta',
                            'substituicao','finalizacao','passe_certo','passe_errado',
                            'escanteio','impedimento','outro')),
    detalhes            JSONB,     -- espaço livre para qualquer outra informação extra
    registrado_por      VARCHAR(120),
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 14. AJUSTES MANUAIS DO CRONÔMETRO (auditoria — cobre o cenário do auxiliar esquecer de iniciar)
CREATE TABLE ajustes_cronometro (
    id                SERIAL PRIMARY KEY,
    partida_id        INTEGER NOT NULL REFERENCES partidas(id),
    segundos_anterior INTEGER NOT NULL,
    segundos_novo     INTEGER NOT NULL,
    periodo_anterior  VARCHAR(20),
    periodo_novo      VARCHAR(20),
    motivo            VARCHAR(120),   -- ex: "esqueceu de iniciar o cronômetro"
    ajustado_por      VARCHAR(120),
    ajustado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 15. CICLOS DA IA (perguntas periódicas de 2-3min + reações a gatilhos + sugestões)
CREATE TABLE ciclos_ia (
    id                SERIAL PRIMARY KEY,
    partida_id        INTEGER NOT NULL REFERENCES partidas(id),
    minuto_jogo       SMALLINT NOT NULL,
    origem            VARCHAR(10) NOT NULL CHECK (origem IN ('ciclo','gatilho')),
    evento_gatilho_id INTEGER REFERENCES eventos_partida(id),  -- preenchido se origem = gatilho
    pergunta_ia       JSONB,   -- pergunta(s) de múltipla escolha geradas pela IA
    resposta_staff    JSONB,
    sugestao_ia       TEXT,    -- tática, substituição e/ou alerta disciplinar
    criado_em         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 16. ESQUEMA TÁTICO USADO NA PARTIDA (pode mudar durante o jogo — histórico por período)
-- Base para entender, ao longo do tempo, qual esquema traz melhor resultado.
CREATE TABLE esquema_tatico_partida (
    id             SERIAL PRIMARY KEY,
    partida_id     INTEGER NOT NULL REFERENCES partidas(id),
    esquema        VARCHAR(20) NOT NULL,   -- ex: 4-3-3, 4-4-2, 3-5-2
    minuto_inicio  SMALLINT NOT NULL,
    minuto_fim     SMALLINT,               -- null enquanto ainda está em vigor
    motivo_mudanca VARCHAR(120),           -- ex: substituição tática, resposta a gol sofrido
    registrado_por VARCHAR(120),
    criado_em      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 17. NOTA DO ATLETA POR PARTIDA (alimenta a nota média em estatisticas_atleta_campeonato)
CREATE TABLE desempenho_atleta_partida (
    id           SERIAL PRIMARY KEY,
    partida_id   INTEGER NOT NULL REFERENCES partidas(id),
    atleta_id    INTEGER NOT NULL REFERENCES atletas(id),
    nota         NUMERIC(3,1) CHECK (nota BETWEEN 0 AND 10),
    observacao   TEXT,
    avaliado_por VARCHAR(120),
    criado_em    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (partida_id, atleta_id)
);

-- 18. RETROSPECTO PÓS-JOGO
-- Gerado automaticamente pela IA quando a partida é finalizada, mas fica como
-- rascunho até alguém da comissão revisar e aprovar.
CREATE TABLE retrospecto_partida (
    id                SERIAL PRIMARY KEY,
    partida_id        INTEGER NOT NULL UNIQUE REFERENCES partidas(id),
    pontos_positivos  TEXT,
    pontos_negativos  TEXT,
    licoes_aprendidas TEXT,
    status            VARCHAR(20) NOT NULL DEFAULT 'rascunho_ia'
                      CHECK (status IN ('rascunho_ia','aprovado')),
    revisado_por      VARCHAR(120),
    revisado_em       TIMESTAMPTZ,
    gerado_em         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 19. ESTATÍSTICAS AGREGADAS POR ATLETA/CAMPEONATO (atualizada após cada partida)
CREATE TABLE estatisticas_atleta_campeonato (
    id                 SERIAL PRIMARY KEY,
    atleta_id          INTEGER NOT NULL REFERENCES atletas(id),
    campeonato_id      INTEGER NOT NULL REFERENCES campeonatos(id),
    jogos_disputados   SMALLINT NOT NULL DEFAULT 0,
    gols               SMALLINT NOT NULL DEFAULT 0,
    assistencias       SMALLINT NOT NULL DEFAULT 0,
    cartoes_amarelos   SMALLINT NOT NULL DEFAULT 0,
    cartoes_vermelhos  SMALLINT NOT NULL DEFAULT 0,
    nota_media         NUMERIC(3,2),
    UNIQUE (atleta_id, campeonato_id)
);

-- 20. HISTÓRICO DE COBRANÇAS DE PÊNALTI (registro do que de fato aconteceu, cobrança a cobrança)
CREATE TABLE penaltis_cobranca (
    id                      SERIAL PRIMARY KEY,
    partida_id              INTEGER NOT NULL REFERENCES partidas(id),
    lado                    VARCHAR(10) NOT NULL CHECK (lado IN ('nosso','adversario')),
    atleta_id               INTEGER REFERENCES atletas(id),   -- preenchido quando lado = nosso
    nome_jogador_adversario VARCHAR(120),                     -- preenchido quando lado = adversario
    ordem                   SMALLINT NOT NULL,
    resultado               VARCHAR(15) NOT NULL CHECK (resultado IN ('gol','perdido','defendido')),
    lado_chute              VARCHAR(10) CHECK (lado_chute IN ('esquerda','centro','direita')),
    criado_em               TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 21. SUGESTÃO DE ORDEM DOS BATEDORES (gerada pela IA antes da disputa começar)
-- Guarda a sugestão E a ordem final escolhida pela comissão, lado a lado — permite
-- comparar depois se seguir a sugestão da IA correlaciona com melhor resultado.
CREATE TABLE penaltis_sugestao_ordem (
    id                        SERIAL PRIMARY KEY,
    partida_id                INTEGER NOT NULL REFERENCES partidas(id),
    atleta_id                 INTEGER NOT NULL REFERENCES atletas(id),
    ordem_sugerida            SMALLINT NOT NULL,
    aproveitamento_historico  NUMERIC(5,2),   -- % de conversão calculado com base em penaltis_cobranca
    motivo                    TEXT,           -- explicação curta da IA para essa posição
    ordem_final               SMALLINT,       -- ordem que a comissão de fato escolheu (pode divergir)
    criado_em                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (partida_id, atleta_id)
);

-- 22. CHAT LIVRE COM O ASSISTENTE TÉCNICO IA
-- partida_id opcional: dá pra conversar durante um jogo específico ou fora de contexto de partida
-- (ex: dúvida geral de tática, pergunta sobre um atleta)
CREATE TABLE mensagens_chat_ia (
    id         SERIAL PRIMARY KEY,
    partida_id INTEGER REFERENCES partidas(id),
    autor      VARCHAR(120),
    mensagem   TEXT NOT NULL,
    resposta   TEXT,
    criado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 23. PATROCINADORES (logos exibidos no rodapé do banner)
CREATE TABLE patrocinadores (
    id         SERIAL PRIMARY KEY,
    clube_id   INTEGER NOT NULL REFERENCES clubes(id),
    nome       VARCHAR(120) NOT NULL,
    logo_url   VARCHAR(255),
    ativo      BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 24. ARTES DE DIVULGAÇÃO (banners para redes sociais — pré e pós-jogo)
-- Geração por template fixo (não IA de imagem). Campos obrigatórios do banner —
-- confronto, horário, data, fase e local — já existem em `partidas`/`adversarios`
-- e são puxados automaticamente, sem precisar duplicar aqui. Foto do jogador é
-- opcional (`jogadores_destaque` pode ficar vazio). Patrocinadores exibidos ficam
-- limitados por `clubes.limite_patrocinadores` (5 ou 10, conforme plano).
CREATE TABLE artes_divulgacao (
    id                     SERIAL PRIMARY KEY,
    partida_id             INTEGER NOT NULL REFERENCES partidas(id),
    tipo                   VARCHAR(10) NOT NULL CHECK (tipo IN ('pre_jogo','pos_jogo')),
    template               VARCHAR(50) NOT NULL DEFAULT 'padrao',
    jogadores_destaque     INTEGER[],   -- ids de atletas.id cujas fotos entram na arte — opcional
    frase_personalizada    VARCHAR(150),  -- slogan/frase motivacional deste banner (default: clubes.slogan)
    patrocinadores_exibidos INTEGER[],  -- ids de patrocinadores.id, até o limite do clube
    arquivo_gerado_url     VARCHAR(255),
    criado_por             VARCHAR(120),
    criado_em              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 25. TRANSCRIÇÕES DE VOZ (auditoria — o que foi falado vs. o que a IA interpretou)
-- Todo comando de voz passa por confirmação visual do auxiliar antes de virar
-- evento/resposta de verdade; esta tabela guarda o histórico bruto pra ajustar a
-- interpretação com o tempo (ex: apelidos que a IA não reconheceu de primeira).
CREATE TABLE transcricoes_voz (
    id                        SERIAL PRIMARY KEY,
    partida_id                INTEGER NOT NULL REFERENCES partidas(id),
    contexto                  VARCHAR(20) NOT NULL CHECK (contexto IN ('evento','resposta_ciclo')),
    transcricao_bruta         TEXT NOT NULL,
    interpretacao             JSONB,    -- resultado estruturado que a IA extraiu do texto
    confirmado_pelo_auxiliar  BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================
-- Índices de apoio para consultas em tempo real
-- =========================================================
CREATE INDEX idx_eventos_partida_partida ON eventos_partida(partida_id);
CREATE INDEX idx_ciclos_ia_partida ON ciclos_ia(partida_id);
CREATE INDEX idx_convocacao_partida ON convocacao(partida_id);
CREATE INDEX idx_comentarios_adversario ON comentarios_adversario(adversario_id);
CREATE UNIQUE INDEX idx_convocacao_link_token ON convocacao(link_token);
CREATE INDEX idx_mensagens_chat_ia_partida ON mensagens_chat_ia(partida_id);

-- =========================================================
-- ANOTAÇÕES PARA DESENVOLVIMENTO FUTURO (ainda não implementado)
-- =========================================================
-- 1. Estruturação comercial em módulos: o projeto tem potencial de virar produto
--    vendido por módulos, com preços/planos separados. A funcionalidade de arte de
--    divulgação (`artes_divulgacao`) é candidata natural a um módulo "plus", separado do
--    módulo principal. Perfil de cliente inicial para venda externa: clubes
--    pequenos/amadores (mesmo perfil do Save). O agrupamento exato dos módulos
--    (quais funcionalidades ficam juntas em cada plano) ainda está em aberto —
--    retomar essa definição depois de validar o produto em uso real no Save.
--    Detalhe de precificação já definido: o limite de patrocinadores exibidos no
--    banner (`clubes.limite_patrocinadores`) é um lever direto de mensalidade —
--    5 patrocinadores no plano padrão, 10 num plano superior com valor maior.
-- 2. Novos módulos identificados para expansão futura do produto (fase 2 — depois
--    de validar a ferramenta na prática, fora do escopo de futebol/tática):
--    a) Associados / sócios torcedores — cadastro, cobrança, benefícios.
--    b) Controle de patrocínio — gestão de patrocinadores e contratos.
--    c) Controle financeiro do clube.
--    d) Venda de produtos do clube (loja).
--    e) Site do clube — vitrine institucional. Meio-termo possível: página pública
--       simples, somente-leitura, puxando dado que já existe no banco (próximos
--       jogos, resultados, elenco, arte de divulgação) em vez de site completo.
--
-- DECISÕES DE ARQUITETURA JÁ CONFIRMADAS (não precisam de nova coluna, só registro):
-- - Auxiliar acessa com o mesmo login da comissão (mesmo sistema de usuário/senha,
--   RBAC), com acesso completo — não há papel restrito separado por enquanto.
-- - Link de confirmação do atleta (`convocacao.link_token`) expira quando a partida
--   é finalizada (`partidas.status = 'finalizada'`) — validado na aplicação contra
--   o status da partida, sem necessidade de coluna de expiração dedicada.
-- - Voz: STT nativo do navegador (Web Speech API), sem custo por uso. Todo comando
--   de voz (evento ou resposta de ciclo) passa por confirmação visual do auxiliar
--   antes de gravar no banco — nunca comita direto, dado o risco de ruído de campo.

-- 27. SESSÕES DE AVALIAÇÃO EM LOTE (link público, sem login, pro técnico avaliar
-- vários atletas de uma vez — mesmo padrão do link de confirmação de presença)
CREATE TABLE sessoes_avaliacao (
    id             SERIAL PRIMARY KEY,
    clube_id       INTEGER NOT NULL REFERENCES clubes(id),
    link_token     UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    avaliador_nome VARCHAR(120),
    status         VARCHAR(20) NOT NULL DEFAULT 'pendente',
    criado_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
    concluido_em   TIMESTAMPTZ
);
