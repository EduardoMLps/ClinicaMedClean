-- =====================================================================
-- Med Flow - migracao 4.0.1 (correcoes de seguranca B3 e B9)
--
-- Para bancos criados ANTES da versao 4.0.1. O backend ja aplica estas
-- mudancas sozinho ao iniciar; este arquivo serve para aplicar manualmente
-- caso o usuario do banco da aplicacao nao tenha permissao de ALTER/CREATE.
--
--   mysql -u root -p clinica_odontologica < database/migracao_4.0.1_seguranca.sql
-- =====================================================================

CREATE TABLE IF NOT EXISTS tokens_revogados (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    jti         VARCHAR(64) NOT NULL,
    usuario_id  BIGINT NULL,
    tipo        VARCHAR(10) NOT NULL DEFAULT 'access',
    expira_em   DATETIME NOT NULL,
    revogado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_tokens_revogados_jti UNIQUE (jti),
    INDEX idx_tokens_revogados_expira (expira_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS revogacoes_sessao_usuario (
    usuario_id  BIGINT NOT NULL PRIMARY KEY,
    revogado_em DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Adiciona usuarios.profissional_id somente se ainda nao existir.
SET @existe := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'usuarios'
      AND COLUMN_NAME = 'profissional_id'
);
SET @sql := IF(@existe = 0,
    'ALTER TABLE usuarios ADD COLUMN profissional_id BIGINT UNSIGNED NULL, ADD CONSTRAINT fk_usuarios_profissional FOREIGN KEY (profissional_id) REFERENCES profissionais (id) ON DELETE SET NULL ON UPDATE CASCADE',
    'SELECT ''usuarios.profissional_id ja existe''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
