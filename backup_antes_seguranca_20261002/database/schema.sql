-- =====================================================================
-- Sistema de Gestao para Clinica Odontologica
-- Schema MySQL 8 (InnoDB)
-- Autor: DBA do time
-- Gerado em: 2026-08-17
--
-- Convencoes:
--   - Todas as tabelas: ENGINE=InnoDB, CHARSET=utf8mb4
--   - Chaves primarias: BIGINT UNSIGNED AUTO_INCREMENT
--   - Timestamps padrao: DATETIME DEFAULT CURRENT_TIMESTAMP
--   - Integridade referencial via FOREIGN KEY em todas as tabelas filhas
-- =====================================================================

CREATE DATABASE IF NOT EXISTS clinica_odontologica
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE clinica_odontologica;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================================
-- MODULO 1: ACESSO E SEGURANCA
-- =====================================================================

-- Perfis de acesso (administrador, dentista, recepcao, financeiro, ...)
CREATE TABLE perfis (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome        VARCHAR(50) NOT NULL,
    CONSTRAINT uq_perfis_nome UNIQUE (nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Usuarios do sistema (login)
CREATE TABLE usuarios (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome        VARCHAR(150) NOT NULL,
    email       VARCHAR(150) NOT NULL,
    senha_hash  VARCHAR(255) NOT NULL,
    perfil_id   BIGINT UNSIGNED NOT NULL,
    ativo       TINYINT(1) NOT NULL DEFAULT 1,
    criado_em   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_usuarios_email UNIQUE (email),
    CONSTRAINT fk_usuarios_perfil FOREIGN KEY (perfil_id)
        REFERENCES perfis (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_usuarios_perfil (perfil_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Permissoes granulares por perfil e recurso (tela/rota/modulo)
CREATE TABLE permissoes (
    id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    perfil_id     BIGINT UNSIGNED NOT NULL,
    recurso       VARCHAR(100) NOT NULL,
    pode_ler      TINYINT(1) NOT NULL DEFAULT 0,
    pode_escrever TINYINT(1) NOT NULL DEFAULT 0,
    CONSTRAINT fk_permissoes_perfil FOREIGN KEY (perfil_id)
        REFERENCES perfis (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT uq_permissoes_perfil_recurso UNIQUE (perfil_id, recurso),
    INDEX idx_permissoes_recurso (recurso)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Log de auditoria (trilha de alteracoes em qualquer tabela do sistema)
CREATE TABLE log_auditoria (
    id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    usuario_id    BIGINT UNSIGNED NULL,
    acao          VARCHAR(50) NOT NULL,
    tabela        VARCHAR(100) NOT NULL,
    registro_id   BIGINT UNSIGNED NULL,
    dados_antes   JSON NULL,
    dados_depois  JSON NULL,
    criado_em     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_log_auditoria_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios (id) ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_log_auditoria_usuario (usuario_id),
    INDEX idx_log_auditoria_tabela_registro (tabela, registro_id),
    INDEX idx_log_auditoria_criado_em (criado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================================
-- MODULO 2: PESSOAS (PACIENTES E PROFISSIONAIS)
-- =====================================================================

-- Especialidades odontologicas (ortodontia, endodontia, etc.)
CREATE TABLE especialidades (
    id    BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome  VARCHAR(100) NOT NULL,
    CONSTRAINT uq_especialidades_nome UNIQUE (nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Profissionais (dentistas) da clinica
CREATE TABLE profissionais (
    id                 BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome               VARCHAR(150) NOT NULL,
    especialidade_id   BIGINT UNSIGNED NOT NULL,
    registro_conselho  VARCHAR(30) NOT NULL,
    ativo              TINYINT(1) NOT NULL DEFAULT 1,
    CONSTRAINT fk_profissionais_especialidade FOREIGN KEY (especialidade_id)
        REFERENCES especialidades (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_profissionais_especialidade (especialidade_id),
    INDEX idx_profissionais_ativo (ativo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Pacientes da clinica
-- Observacao: a FK de consentimento_lgpd_id para consentimentos_lgpd.id
-- e adicionada via ALTER TABLE no final do arquivo, pois consentimentos_lgpd
-- referencia pacientes.id (dependencia circular entre as duas tabelas).
CREATE TABLE pacientes (
    id                     BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome                   VARCHAR(150) NOT NULL,
    cpf                    VARCHAR(14) NULL,
    data_nascimento        DATE NOT NULL,
    responsavel_id         BIGINT UNSIGNED NULL,
    telefone               VARCHAR(20) NULL,
    email                  VARCHAR(150) NULL,
    consentimento_lgpd_id  BIGINT UNSIGNED NULL,
    criado_em              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_pacientes_cpf UNIQUE (cpf),
    CONSTRAINT fk_pacientes_responsavel FOREIGN KEY (responsavel_id)
        REFERENCES pacientes (id) ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_pacientes_responsavel (responsavel_id),
    INDEX idx_pacientes_nome (nome),
    FULLTEXT INDEX ft_pacientes_nome (nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Enderecos dos pacientes
CREATE TABLE enderecos (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    paciente_id  BIGINT UNSIGNED NOT NULL,
    logradouro   VARCHAR(200) NOT NULL,
    cidade       VARCHAR(100) NOT NULL,
    uf           CHAR(2) NOT NULL,
    cep          VARCHAR(9) NOT NULL,
    CONSTRAINT fk_enderecos_paciente FOREIGN KEY (paciente_id)
        REFERENCES pacientes (id) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_enderecos_paciente (paciente_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================================
-- MODULO 3: AGENDA
-- =====================================================================

-- Cadeiras/consultorios fisicos da clinica
CREATE TABLE cadeiras_consultorio (
    id    BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome  VARCHAR(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Agendamentos de consultas
CREATE TABLE agendamentos (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    paciente_id     BIGINT UNSIGNED NOT NULL,
    profissional_id BIGINT UNSIGNED NOT NULL,
    cadeira_id      BIGINT UNSIGNED NULL,
    inicio          DATETIME NOT NULL,
    fim             DATETIME NOT NULL,
    status          ENUM('agendado','confirmado','em_atendimento','concluido','faltou','cancelado')
                    NOT NULL DEFAULT 'agendado',
    CONSTRAINT fk_agendamentos_paciente FOREIGN KEY (paciente_id)
        REFERENCES pacientes (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_agendamentos_profissional FOREIGN KEY (profissional_id)
        REFERENCES profissionais (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_agendamentos_cadeira FOREIGN KEY (cadeira_id)
        REFERENCES cadeiras_consultorio (id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_agendamentos_periodo CHECK (fim > inicio),
    INDEX idx_agendamentos_paciente (paciente_id),
    INDEX idx_agendamentos_profissional (profissional_id),
    INDEX idx_agendamentos_inicio (inicio),
    INDEX idx_agendamentos_profissional_inicio (profissional_id, inicio),
    INDEX idx_agendamentos_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Bloqueios de agenda (ferias, folgas, eventos) por profissional
CREATE TABLE bloqueios_agenda (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    profissional_id BIGINT UNSIGNED NOT NULL,
    inicio          DATETIME NOT NULL,
    fim             DATETIME NOT NULL,
    motivo          VARCHAR(255) NULL,
    CONSTRAINT fk_bloqueios_profissional FOREIGN KEY (profissional_id)
        REFERENCES profissionais (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_bloqueios_periodo CHECK (fim > inicio),
    INDEX idx_bloqueios_profissional (profissional_id),
    INDEX idx_bloqueios_inicio (inicio)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================================
-- MODULO 4: CLINICO (PRONTUARIO, ODONTOGRAMA, DOCUMENTOS)
-- =====================================================================

-- Prontuario clinico do paciente
CREATE TABLE prontuarios (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    paciente_id     BIGINT UNSIGNED NOT NULL,
    profissional_id BIGINT UNSIGNED NOT NULL,
    criado_em       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_prontuarios_paciente FOREIGN KEY (paciente_id)
        REFERENCES pacientes (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_prontuarios_profissional FOREIGN KEY (profissional_id)
        REFERENCES profissionais (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_prontuarios_paciente (paciente_id),
    INDEX idx_prontuarios_profissional (profissional_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Evolucoes clinicas (registros de atendimento dentro do prontuario)
CREATE TABLE evolucoes_clinicas (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    prontuario_id   BIGINT UNSIGNED NOT NULL,
    profissional_id BIGINT UNSIGNED NOT NULL,
    texto           TEXT NOT NULL,
    criado_em       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_evolucoes_prontuario FOREIGN KEY (prontuario_id)
        REFERENCES prontuarios (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_evolucoes_profissional FOREIGN KEY (profissional_id)
        REFERENCES profissionais (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_evolucoes_prontuario (prontuario_id),
    INDEX idx_evolucoes_profissional (profissional_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Odontograma (situacao por dente/face do paciente)
CREATE TABLE odontograma (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    paciente_id     BIGINT UNSIGNED NOT NULL,
    dente_fdi       TINYINT UNSIGNED NOT NULL,
    face            ENUM('oclusal','mesial','distal','vestibular','lingual') NOT NULL,
    situacao        VARCHAR(60) NOT NULL,
    registrado_em   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    profissional_id BIGINT UNSIGNED NOT NULL,
    CONSTRAINT fk_odontograma_paciente FOREIGN KEY (paciente_id)
        REFERENCES pacientes (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_odontograma_profissional FOREIGN KEY (profissional_id)
        REFERENCES profissionais (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_odontograma_dente_fdi CHECK (dente_fdi BETWEEN 11 AND 85),
    INDEX idx_odontograma_paciente (paciente_id),
    INDEX idx_odontograma_profissional (profissional_id),
    INDEX idx_odontograma_dente (paciente_id, dente_fdi)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Historico de alteracoes do odontograma
CREATE TABLE odontograma_historico (
    id                 BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    odontograma_id     BIGINT UNSIGNED NOT NULL,
    situacao_anterior  VARCHAR(60) NOT NULL,
    alterado_em        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_odontograma_hist_odontograma FOREIGN KEY (odontograma_id)
        REFERENCES odontograma (id) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_odontograma_hist_odontograma (odontograma_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Exames e anexos (radiografias, fotos, laudos) do paciente
CREATE TABLE exames_anexos (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    paciente_id  BIGINT UNSIGNED NOT NULL,
    tipo         VARCHAR(60) NOT NULL,
    arquivo_url  VARCHAR(500) NOT NULL,
    enviado_em   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_exames_anexos_paciente FOREIGN KEY (paciente_id)
        REFERENCES pacientes (id) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_exames_anexos_paciente (paciente_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Receitas emitidas a partir do prontuario
CREATE TABLE receitas (
    id             BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    prontuario_id  BIGINT UNSIGNED NOT NULL,
    texto          TEXT NOT NULL,
    emitido_em     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_receitas_prontuario FOREIGN KEY (prontuario_id)
        REFERENCES prontuarios (id) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_receitas_prontuario (prontuario_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Atestados emitidos a partir do prontuario
CREATE TABLE atestados (
    id                 BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    prontuario_id      BIGINT UNSIGNED NOT NULL,
    texto              TEXT NOT NULL,
    dias_afastamento   SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    emitido_em         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_atestados_prontuario FOREIGN KEY (prontuario_id)
        REFERENCES prontuarios (id) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_atestados_prontuario (prontuario_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================================
-- MODULO 5: ORCAMENTO / PLANO DE TRATAMENTO
-- =====================================================================

-- Catalogo de procedimentos odontologicos
CREATE TABLE procedimentos (
    id     BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome   VARCHAR(150) NOT NULL,
    preco  DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    INDEX idx_procedimentos_nome (nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Orcamentos propostos ao paciente
CREATE TABLE orcamentos (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    paciente_id  BIGINT UNSIGNED NOT NULL,
    status       ENUM('pendente','aprovado','recusado') NOT NULL DEFAULT 'pendente',
    total        DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    criado_em    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_orcamentos_paciente FOREIGN KEY (paciente_id)
        REFERENCES pacientes (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_orcamentos_paciente (paciente_id),
    INDEX idx_orcamentos_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Itens de um orcamento (procedimentos e quantidades)
CREATE TABLE orcamento_itens (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    orcamento_id    BIGINT UNSIGNED NOT NULL,
    procedimento_id BIGINT UNSIGNED NOT NULL,
    quantidade      SMALLINT UNSIGNED NOT NULL DEFAULT 1,
    valor_unit      DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_orcamento_itens_orcamento FOREIGN KEY (orcamento_id)
        REFERENCES orcamentos (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_orcamento_itens_procedimento FOREIGN KEY (procedimento_id)
        REFERENCES procedimentos (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_orcamento_itens_orcamento (orcamento_id),
    INDEX idx_orcamento_itens_procedimento (procedimento_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Planos de tratamento originados de um orcamento aprovado
CREATE TABLE planos_tratamento (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    orcamento_id BIGINT UNSIGNED NOT NULL,
    paciente_id  BIGINT UNSIGNED NOT NULL,
    status       ENUM('planejado','em_andamento','concluido','cancelado') NOT NULL DEFAULT 'planejado',
    iniciado_em  DATETIME NULL,
    CONSTRAINT fk_planos_tratamento_orcamento FOREIGN KEY (orcamento_id)
        REFERENCES orcamentos (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_planos_tratamento_paciente FOREIGN KEY (paciente_id)
        REFERENCES pacientes (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_planos_tratamento_orcamento (orcamento_id),
    INDEX idx_planos_tratamento_paciente (paciente_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================================
-- MODULO 6: FINANCEIRO
-- =====================================================================

-- Convenios odontologicos aceitos pela clinica
CREATE TABLE convenios (
    id    BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome  VARCHAR(150) NOT NULL,
    CONSTRAINT uq_convenios_nome UNIQUE (nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de precos negociados por convenio/procedimento
CREATE TABLE tabela_precos_convenio (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    convenio_id     BIGINT UNSIGNED NOT NULL,
    procedimento_id BIGINT UNSIGNED NOT NULL,
    preco           DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_tabela_precos_convenio FOREIGN KEY (convenio_id)
        REFERENCES convenios (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_tabela_precos_procedimento FOREIGN KEY (procedimento_id)
        REFERENCES procedimentos (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT uq_tabela_precos_convenio_procedimento UNIQUE (convenio_id, procedimento_id),
    INDEX idx_tabela_precos_convenio (convenio_id),
    INDEX idx_tabela_precos_procedimento (procedimento_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Contas a receber (parcelas geradas a partir de orcamentos)
CREATE TABLE contas_receber (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    orcamento_id BIGINT UNSIGNED NULL,
    paciente_id  BIGINT UNSIGNED NOT NULL,
    valor        DECIMAL(10,2) NOT NULL,
    vencimento   DATE NOT NULL,
    status       ENUM('pendente','pago','atrasado','cancelado') NOT NULL DEFAULT 'pendente',
    CONSTRAINT fk_contas_receber_orcamento FOREIGN KEY (orcamento_id)
        REFERENCES orcamentos (id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_contas_receber_paciente FOREIGN KEY (paciente_id)
        REFERENCES pacientes (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_contas_receber_orcamento (orcamento_id),
    INDEX idx_contas_receber_paciente (paciente_id),
    INDEX idx_contas_receber_vencimento (vencimento),
    INDEX idx_contas_receber_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Contas a pagar (despesas da clinica)
CREATE TABLE contas_pagar (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    descricao   VARCHAR(200) NOT NULL,
    valor       DECIMAL(10,2) NOT NULL,
    vencimento  DATE NOT NULL,
    status      ENUM('pendente','pago','atrasado','cancelado') NOT NULL DEFAULT 'pendente',
    INDEX idx_contas_pagar_vencimento (vencimento),
    INDEX idx_contas_pagar_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Pagamentos efetivamente recebidos
CREATE TABLE pagamentos (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    orcamento_id BIGINT UNSIGNED NULL,
    valor        DECIMAL(10,2) NOT NULL,
    forma        ENUM('dinheiro','cartao','pix','convenio') NOT NULL,
    pago_em      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pagamentos_orcamento FOREIGN KEY (orcamento_id)
        REFERENCES orcamentos (id) ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_pagamentos_orcamento (orcamento_id),
    INDEX idx_pagamentos_pago_em (pago_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Comissoes de profissionais sobre orcamentos executados
CREATE TABLE comissoes_profissionais (
    id               BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    profissional_id  BIGINT UNSIGNED NOT NULL,
    orcamento_id     BIGINT UNSIGNED NOT NULL,
    percentual       DECIMAL(5,2) NOT NULL,
    valor_calculado  DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_comissoes_profissional FOREIGN KEY (profissional_id)
        REFERENCES profissionais (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_comissoes_orcamento FOREIGN KEY (orcamento_id)
        REFERENCES orcamentos (id) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_comissoes_profissional (profissional_id),
    INDEX idx_comissoes_orcamento (orcamento_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================================
-- MODULO 7: ESTOQUE
-- =====================================================================

-- Produtos e materiais de consumo da clinica
CREATE TABLE produtos_estoque (
    id                 BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome               VARCHAR(150) NOT NULL,
    quantidade         INT NOT NULL DEFAULT 0,
    quantidade_minima  INT NOT NULL DEFAULT 0,
    unidade            VARCHAR(20) NOT NULL,
    INDEX idx_produtos_estoque_nome (nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Movimentacoes de entrada/saida de estoque
CREATE TABLE movimentacoes_estoque (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    produto_id  BIGINT UNSIGNED NOT NULL,
    tipo        ENUM('entrada','saida') NOT NULL,
    quantidade  INT NOT NULL,
    motivo      VARCHAR(200) NULL,
    criado_em   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_movimentacoes_produto FOREIGN KEY (produto_id)
        REFERENCES produtos_estoque (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_movimentacoes_quantidade CHECK (quantidade > 0),
    INDEX idx_movimentacoes_produto (produto_id),
    INDEX idx_movimentacoes_criado_em (criado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================================
-- MODULO 8: COMUNICACAO / CONFIGURACAO / LGPD
-- =====================================================================

-- Consentimentos LGPD assinados pelo paciente (ou responsavel)
CREATE TABLE consentimentos_lgpd (
    id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    paciente_id   BIGINT UNSIGNED NOT NULL,
    texto_versao  VARCHAR(20) NOT NULL,
    aceito_em     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_consentimentos_paciente FOREIGN KEY (paciente_id)
        REFERENCES pacientes (id) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_consentimentos_paciente (paciente_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Notificacoes enviadas ao paciente (lembretes, confirmacoes, etc.)
CREATE TABLE notificacoes_enviadas (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    paciente_id  BIGINT UNSIGNED NOT NULL,
    canal        ENUM('whatsapp','sms','email') NOT NULL,
    mensagem     TEXT NOT NULL,
    enviado_em   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notificacoes_paciente FOREIGN KEY (paciente_id)
        REFERENCES pacientes (id) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_notificacoes_paciente (paciente_id),
    INDEX idx_notificacoes_enviado_em (enviado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Pesquisas de satisfacao respondidas pelo paciente
CREATE TABLE pesquisas_satisfacao (
    id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    paciente_id   BIGINT UNSIGNED NOT NULL,
    nota          TINYINT UNSIGNED NOT NULL,
    comentario    TEXT NULL,
    respondido_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pesquisas_paciente FOREIGN KEY (paciente_id)
        REFERENCES pacientes (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_pesquisas_nota CHECK (nota BETWEEN 0 AND 10),
    INDEX idx_pesquisas_paciente (paciente_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Notas fiscais de servico emitidas para pagamentos
CREATE TABLE notas_fiscais_servico (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    pagamento_id BIGINT UNSIGNED NOT NULL,
    numero       VARCHAR(50) NOT NULL,
    emitido_em   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notas_fiscais_pagamento FOREIGN KEY (pagamento_id)
        REFERENCES pagamentos (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT uq_notas_fiscais_numero UNIQUE (numero),
    INDEX idx_notas_fiscais_pagamento (pagamento_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Configuracoes gerais da clinica (chave/valor)
CREATE TABLE configuracoes_clinica (
    id     BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    chave  VARCHAR(100) NOT NULL,
    valor  TEXT NULL,
    CONSTRAINT uq_configuracoes_chave UNIQUE (chave)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================================
-- CONSTRAINTS ADICIONAIS (dependencias circulares resolvidas apos
-- a criacao de todas as tabelas)
-- =====================================================================

ALTER TABLE pacientes
    ADD CONSTRAINT fk_pacientes_consentimento FOREIGN KEY (consentimento_lgpd_id)
        REFERENCES consentimentos_lgpd (id) ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE pacientes
    ADD INDEX idx_pacientes_consentimento (consentimento_lgpd_id);

-- =====================================================================
-- SEED MINIMO (dados iniciais para o sistema funcionar em dev/deploy)
-- =====================================================================

-- Perfis padrao
INSERT INTO perfis (nome) VALUES
    ('administrador'),
    ('dentista'),
    ('recepcao'),
    ('financeiro');

-- Usuario administrador de exemplo
-- ATENCAO: senha_hash abaixo e um placeholder. TROCAR_NO_DEPLOY antes de
-- subir para producao (gerar hash real, ex.: bcrypt/argon2).
INSERT INTO usuarios (nome, email, senha_hash, perfil_id, ativo)
VALUES (
    'Administrador do Sistema',
    'admin@clinica.local',
    'TROCAR_NO_DEPLOY_HASH_PLACEHOLDER',
    (SELECT id FROM perfis WHERE nome = 'administrador'),
    1
);

-- Permissoes basicas de exemplo para o perfil administrador (acesso total)
INSERT INTO permissoes (perfil_id, recurso, pode_ler, pode_escrever)
VALUES
    ((SELECT id FROM perfis WHERE nome = 'administrador'), 'pacientes', 1, 1),
    ((SELECT id FROM perfis WHERE nome = 'administrador'), 'agendamentos', 1, 1),
    ((SELECT id FROM perfis WHERE nome = 'administrador'), 'financeiro', 1, 1),
    ((SELECT id FROM perfis WHERE nome = 'administrador'), 'estoque', 1, 1),
    ((SELECT id FROM perfis WHERE nome = 'administrador'), 'configuracoes', 1, 1);

-- Cadeira de consultorio padrao (exemplo minimo)
INSERT INTO cadeiras_consultorio (nome) VALUES ('Cadeira 1');

-- Fim do schema
