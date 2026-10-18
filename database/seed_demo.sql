-- =====================================================================
-- SEED DE DEMONSTRAÇÃO — dados fictícios apenas para teste do sistema.
-- NÃO usar em produção. Nenhum dado aqui corresponde a pessoas reais.
-- Pressupõe que schema.sql já foi aplicado (tabelas + seed de perfis).
-- =====================================================================

USE clinica_odontologica;
SET NAMES utf8mb4;

-- ---------------------------------------------------------------------
-- Senha de demonstração do usuário administrador.
--
-- schema.sql cria 'admin@clinica.local' com um hash placeholder
-- ('TROCAR_NO_DEPLOY_HASH_PLACEHOLDER') que NUNCA autentica — de propósito,
-- para que uma cópia de produção não suba com uma senha padrão conhecida.
-- Como este script é só para ambiente de teste/demonstração, definimos
-- aqui uma senha real (bcrypt) só para você conseguir logar localmente:
--
--   E-mail: admin@clinica.local
--   Senha:  TesteSenha123!
--
-- NUNCA rode este UPDATE contra um banco de produção.
UPDATE usuarios
SET senha_hash = '$2b$12$SqW9tsx/yzKP5cL.2xTPO.lRs7yCl1jPPrGcaM3bkjOtC9xbUiQ9O'
WHERE email = 'admin@clinica.local';

-- ---------------------------------------------------------------------
-- Especialidades e profissionais
-- ---------------------------------------------------------------------
INSERT INTO especialidades (nome) VALUES
  ('Clínico Geral'), ('Ortodontia'), ('Endodontia')
ON DUPLICATE KEY UPDATE nome = VALUES(nome);

INSERT INTO profissionais (nome, especialidade_id, registro_conselho, ativo) VALUES
  ('Dra. Camila Ferreira', (SELECT id FROM especialidades WHERE nome='Clínico Geral'), 'CRO-PR 12345', 1),
  ('Dr. Rodrigo Almeida',  (SELECT id FROM especialidades WHERE nome='Ortodontia'),    'CRO-PR 23456', 1),
  ('Dra. Beatriz Nogueira',(SELECT id FROM especialidades WHERE nome='Endodontia'),    'CRO-PR 34567', 1);

-- schema.sql já cria 'Cadeira 1' no seed padrão — evita duplicar aqui.
INSERT INTO cadeiras_consultorio (nome)
  SELECT 'Cadeira 1' WHERE NOT EXISTS (SELECT 1 FROM cadeiras_consultorio WHERE nome = 'Cadeira 1');
INSERT INTO cadeiras_consultorio (nome)
  SELECT 'Cadeira 2' WHERE NOT EXISTS (SELECT 1 FROM cadeiras_consultorio WHERE nome = 'Cadeira 2');

-- ---------------------------------------------------------------------
-- 10 pacientes de teste (2 deles menores de idade, com responsável)
-- ---------------------------------------------------------------------
INSERT INTO pacientes (nome, cpf, data_nascimento, telefone, email) VALUES
  ('Ana Beatriz Souza',      '111.222.333-01', '1990-03-14', '(41) 90001-0001', 'ana.souza@teste.com'),
  ('João Pedro Lima',        '111.222.333-02', '1985-07-22', '(41) 90001-0002', 'joao.lima@teste.com'),
  ('Maria Clara Rodrigues',  '111.222.333-03', '2001-11-05', '(41) 90001-0003', 'maria.rodrigues@teste.com'),
  ('Carlos Eduardo Santos',  '111.222.333-04', '1978-01-30', '(41) 90001-0004', 'carlos.santos@teste.com'),
  ('Fernanda Oliveira',      '111.222.333-05', '1995-09-18', '(41) 90001-0005', 'fernanda.oliveira@teste.com'),
  ('Lucas Gabriel Costa',    '111.222.333-06', '1988-05-02', '(41) 90001-0006', 'lucas.costa@teste.com'),
  ('Patrícia Mendes',        '111.222.333-07', '1970-12-25', '(41) 90001-0007', 'patricia.mendes@teste.com'),
  ('Rafael Barbosa',         '111.222.333-08', '1999-04-09', '(41) 90001-0008', 'rafael.barbosa@teste.com'),
  ('Sofia Barbosa',          NULL,             '2014-06-17', NULL,              NULL), -- menor, resp.: Rafael Barbosa
  ('Heitor Souza',           NULL,             '2016-02-28', NULL,              NULL); -- menor, resp.: Ana Beatriz Souza

UPDATE pacientes SET responsavel_id = (SELECT id FROM (SELECT id FROM pacientes WHERE nome='Rafael Barbosa') t)
  WHERE nome = 'Sofia Barbosa';
UPDATE pacientes SET responsavel_id = (SELECT id FROM (SELECT id FROM pacientes WHERE nome='Ana Beatriz Souza') t)
  WHERE nome = 'Heitor Souza';

-- Consentimento LGPD para cada um dos 10 pacientes (FK circular: cria depois, atualiza o paciente)
INSERT INTO consentimentos_lgpd (paciente_id, texto_versao)
  SELECT id, 'v1.0' FROM pacientes WHERE consentimento_lgpd_id IS NULL;

UPDATE pacientes p
  JOIN consentimentos_lgpd c ON c.paciente_id = p.id
  SET p.consentimento_lgpd_id = c.id
  WHERE p.consentimento_lgpd_id IS NULL;

-- ---------------------------------------------------------------------
-- Procedimentos (catálogo básico)
-- ---------------------------------------------------------------------
INSERT INTO procedimentos (nome, preco) VALUES
  ('Consulta / avaliação', 120.00),
  ('Limpeza (profilaxia)', 150.00),
  ('Restauração simples', 180.00),
  ('Extração simples', 200.00),
  ('Canal (endodontia)', 850.00),
  ('Manutenção de aparelho ortodôntico', 220.00);

-- ---------------------------------------------------------------------
-- Agendamentos de teste (mistura de status, próximos dias)
-- ---------------------------------------------------------------------
INSERT INTO agendamentos (paciente_id, profissional_id, cadeira_id, inicio, fim, status)
SELECT p.id, pr.id, c.id,
       DATE_ADD(CURDATE(), INTERVAL dt.dias DAY) + INTERVAL dt.min_ini MINUTE,
       DATE_ADD(CURDATE(), INTERVAL dt.dias DAY) + INTERVAL dt.min_fim MINUTE,
       dt.status
FROM (
  SELECT 'Ana Beatriz Souza'      AS paciente, 'Dra. Camila Ferreira'  AS prof, 'Cadeira 1' AS cadeira, 1 AS dias, 540 AS min_ini, 570 AS min_fim, 'agendado'    AS status
  UNION ALL SELECT 'João Pedro Lima',       'Dr. Rodrigo Almeida',   'Cadeira 2', 1,  600, 630, 'confirmado'
  UNION ALL SELECT 'Maria Clara Rodrigues', 'Dra. Beatriz Nogueira', 'Cadeira 1', 2,  840, 900, 'agendado'
  UNION ALL SELECT 'Carlos Eduardo Santos', 'Dra. Camila Ferreira',  'Cadeira 1', 0,  480, 510, 'concluido'
  UNION ALL SELECT 'Fernanda Oliveira',     'Dr. Rodrigo Almeida',   'Cadeira 2', 0,  660, 690, 'faltou'
  UNION ALL SELECT 'Lucas Gabriel Costa',   'Dra. Beatriz Nogueira', 'Cadeira 1', 3,  900, 930, 'agendado'
  UNION ALL SELECT 'Patrícia Mendes',       'Dra. Camila Ferreira',  'Cadeira 2', 1,  960, 990, 'confirmado'
  UNION ALL SELECT 'Rafael Barbosa',        'Dr. Rodrigo Almeida',   'Cadeira 1', 4,  540, 570, 'agendado'
  UNION ALL SELECT 'Sofia Barbosa',         'Dra. Camila Ferreira',  'Cadeira 2', 2,  600, 630, 'agendado'
  UNION ALL SELECT 'Heitor Souza',          'Dra. Beatriz Nogueira', 'Cadeira 1', 5,  780, 810, 'agendado'
) dt
JOIN pacientes p ON p.nome = dt.paciente
JOIN (SELECT nome, MIN(id) AS id FROM profissionais GROUP BY nome) pr ON pr.nome = dt.prof
JOIN (SELECT nome, MIN(id) AS id FROM cadeiras_consultorio GROUP BY nome) c ON c.nome = dt.cadeira;

-- ---------------------------------------------------------------------
-- Um orçamento de exemplo, para testar o módulo financeiro
-- ---------------------------------------------------------------------
INSERT INTO orcamentos (paciente_id, status, total)
  SELECT id, 'aprovado', 330.00 FROM pacientes WHERE nome = 'Ana Beatriz Souza';

INSERT INTO orcamento_itens (orcamento_id, procedimento_id, quantidade, valor_unit)
  SELECT o.id, pc.id, 1, pc.preco
  FROM orcamentos o, procedimentos pc
  WHERE o.paciente_id = (SELECT id FROM pacientes WHERE nome='Ana Beatriz Souza')
    AND pc.nome IN ('Consulta / avaliação','Limpeza (profilaxia)');

INSERT INTO contas_receber (orcamento_id, paciente_id, valor, vencimento, status)
  SELECT o.id, o.paciente_id, o.total, DATE_ADD(CURDATE(), INTERVAL 15 DAY), 'pendente'
  FROM orcamentos o WHERE o.paciente_id = (SELECT id FROM pacientes WHERE nome='Ana Beatriz Souza');

-- ---------------------------------------------------------------------
-- Estoque de exemplo
-- ---------------------------------------------------------------------
INSERT INTO produtos_estoque (nome, quantidade, quantidade_minima, unidade) VALUES
  ('Luva de procedimento (caixa)', 8, 5, 'caixa'),
  ('Anestésico odontológico', 3, 5, 'unidade'),
  ('Resina composta', 12, 4, 'unidade');

SELECT 'Seed de demonstração aplicado com sucesso.' AS resultado;
