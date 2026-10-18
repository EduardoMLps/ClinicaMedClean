# Histórico de versões do Med Flow

Registro das mudanças do sistema da clínica. A versão mais recente fica no topo.

## Agenda semanal (17/10/2026)

- A Agenda ganhou a visualização **Semana**, que passa a ser a tela inicial da Agenda
  (a lista do dia continua na aba **Dia (lista)**): um cronograma
  de domingo a sábado, das 08:00 às 19:00, com todas as consultas da semana.
- Cada consulta é um bloco com horário de início e fim, paciente, dentista e
  procedimento, com altura proporcional à duração e cor por dentista. Consultas no
  mesmo horário (cadeiras diferentes) ficam lado a lado.
- Domingo (fechado) e o almoço (12:00 às 13:30) aparecem hachurados; o dia de hoje
  fica destacado, com uma linha vermelha no horário atual.
- Clicar em uma consulta mostra os detalhes e permite mudar o status, receber o
  pagamento ou abrir o prontuário. Clicar em um horário livre abre o novo
  agendamento já com a data e a hora preenchidas.
- Botões de semana anterior, próxima e "Esta semana"; o filtro de profissional
  também vale para a semana.
- Backup: `SISTEMA_CLINICA_BACKUP_20261017_antes_agenda_semanal.html`.
- Testes: os casos AGE de `tests/test_medflow_e2e.py` agora clicam em **Dia (lista)**
  antes de conferir a tabela do dia.

## Nova página Odontograma (17/10/2026)

- Novo item **Odontograma** no menu lateral do `SISTEMA_CLINICA.html`.
- Seleciona o paciente e mostra todos os dentes (permanentes ou decíduos, numeração FDI),
  com o status de cada um: **0 = hígido**, **1 = cariado**, **2 = restaurado**.
- O status é alterado com os botões 0, 1 e 2 abaixo de cada dente e salvo na hora,
  com contagem por status no topo.
- Usa os mesmos dados do odontograma do Prontuário: as alterações aparecem nas duas
  telas. Dentes com outro estado do Prontuário (canal, coroa etc.) aparecem com o nome
  do estado e podem ser trocados para 0, 1 ou 2, mantendo faces e observação.
- Backup: `SISTEMA_CLINICA_BACKUP_20261017_v5.2.html`.

## Versão 5.2 (05/10/2026)

Revisão do módulo de RH e do gerador de contracheque.

### Correções
- Salário pago antes da admissão: quem era admitido em setembro aparecia com
  salário cheio desde janeiro. Agora nada é pago antes da admissão e o mês de
  entrada é proporcional (mês comercial de 30 dias).
- Desligamento: novo campo de data. O mês da saída é proporcional e os meses
  seguintes ficam sem pagamento; inativar sem data registra o desligamento hoje.
- Funcionários de outros cargos eram gravados com 25% de comissão por padrão;
  agora a comissão vale só para dentistas.
- Mudar o cargo de um colaborador para Dentista agora o inclui na Agenda.
- A comissão passa a usar o valor cobrado no recebimento; mudar o preço de um
  procedimento depois não altera comissões já calculadas.
- O contracheque mostrava "Base INSS" para estagiários e prestadores PJ, que não
  têm esse desconto.
- Em celular, a tabela de valores do contracheque cortava a coluna Descontos.

### Melhorias
- Cadastro de colaboradores com CPF (validado e sem repetição) e dependentes
  para o IRRF (R$ 189,59 por dependente).
- Contracheque com CPF, período, dependentes, data de desligamento, valor
  líquido por extenso, base do FGTS, prazo de pagamento da CLT e local e data na
  assinatura. Título conforme o vínculo: recibo de salário (CLT), RPA
  (autônomo), recibo de bolsa-estágio ou demonstrativo (PJ).
- IRRF também calculado para a bolsa-estágio.
- Folha do mês com coluna de dias trabalhados e indicadores de FGTS, custo total
  de pessoal (comissões, salários e FGTS) e provisão de 13º e férias.
- **Lançar folha no Financeiro** também lança o FGTS e usa o salário
  proporcional.
- Novo botão **Exportar folha (CSV)**.
- Busca por nome, cargo ou CPF e filtro por situação na lista de colaboradores.

### Testes
- 185 de 185 casos aprovados em `tests/test_medflow_e2e.py`, com 13 novos casos
  do RH (V52-01 a V52-13). O caso AGE-13 passou a calcular o próximo domingo,
  em vez de usar uma data fixa que já tinha passado.

### Backup
- Versão 5.1 preservada em `SISTEMA_CLINICA_BACKUP_20261005_v5.1.html`.

## Versão 5.1 (02/10/2026)

Versão de consolidação: reúne o módulo de RH (5.0) e as correções de segurança
do backend (4.0.1), sem mudança de regras de negócio.

### Segurança e testes
- Pendências B1 a B14 do backend corrigidas e conferidas. Resta o MFA.
- Testes finais: 172 de 172 no `SISTEMA_CLINICA.html`, 41 de 41 em
  `tests/test_backend_seguranca.py`, 17 de 17 em
  `tests/test_backend_independente.py` (novo) e `pip-audit` sem vulnerabilidades.

### Documentação
- README, `docs/TESTES_E_SEGURANCA_5.1.md` (novo), `docs/Configuração do Sistema.pdf`
  e `banco01.docx` atualizados para a versão 5.1.
- Versão 5.1 exibida no menu lateral, na tela de acesso e no Dashboard.

### Backup
- Versão 5.0 preservada em `SISTEMA_CLINICA_BACKUP_20261002_v5.0.html`.

## Versão 5.0 (02/10/2026)

### RH (novo módulo)
- Novo item **RH** no menu, com as abas **Colaboradores** e **Comissões e folha**.
- Cadastro de colaboradores com cargo, vínculo (CLT ou autônomo), salário,
  percentual de comissão e data de admissão. Dentistas novos entram também na
  lista de profissionais da Agenda.
- Colaboradores de demonstração: os 3 dentistas da clínica (25% de comissão) e
  3 funcionários CLT (recepção, auxiliar de saúde bucal e gerência administrativa).
- Percentual padrão de comissão configurável (25%); valores fora de 0 a 100 são recusados.

### Comissão dos dentistas
- Cada dentista recebe 25% (ou o percentual do seu cadastro) do valor dos
  atendimentos concluídos e pagos no período.
- Botão **Lançar folha no Financeiro**: cria as despesas de comissão
  (categoria Comissões) e de salários (categoria Pessoal) do mês, sem duplicar
  lançamentos já feitos.

### Relatórios com totais
- Relatórios diário, semanal, mensal e anual passam a exibir o quadro **Totais
  do período**: recebido, despesas, comissões dos dentistas e resultado líquido.
- Tabela de comissões por dentista com linha TOTAL em todos os relatórios.
- Gráficos e tabelas com linha de total; o relatório anual ganhou as colunas
  Despesas, Comissões e Resultado líquido por mês.
- As comissões lançadas no Financeiro não são somadas duas vezes no resultado.

### Ganhos dos dentistas (nova aba em Relatórios)
- Produção paga, comissão bruta, descontos (INSS e IRRF) e comissão líquida por
  dentista, com total geral, gráfico e acumulado do ano.

### Contracheque
- Contracheque individual para cada colaborador (dentista ou CLT), com
  proventos, descontos, valor líquido, base de INSS, base de IRRF e FGTS (CLT).
- Cálculo com as tabelas de 2026: INSS progressivo (CLT), INSS de 11% para
  autônomo, IRRF com desconto simplificado e redução da Lei 15.270/2025.
- Botões para abrir, imprimir um contracheque ou imprimir todos os do mês.
- Os valores são de referência e devem ser conferidos pelo contador da clínica.

### Testes
- 172 casos automatizados aprovados (153 da versão 4.0 e 19 novos de RH,
  comissões, totais, ganhos e contracheque), sem XSS e sem erros de JavaScript.
  Detalhes em `docs/TESTES_E_SEGURANCA_5.0.md`.
- Testes finais de 02/10/2026, depois das correções da 4.0.1: 172 de 172 no sistema da
  clínica, 41 de 41 no backend, 17 testes independentes de ataque (novo
  `tests/test_backend_independente.py`) e `pip-audit` sem vulnerabilidades.

### Backup
- Versão 4.0 preservada em `SISTEMA_CLINICA_BACKUP_20261002_v4.html`.

## Versão 4.0.1 (02/10/2026): segurança do backend

Fecha as pendências B1 a B14 do relatório de testes da 4.0. O detalhamento está em `docs/SECURITY.md`. São 41 testes automatizados novos (`tests/test_backend_seguranca.py`), todos passando.

### Importante ao atualizar
- **Vincule cada dentista ao seu profissional** (Usuários → `profissional_id`). Sem o vínculo, o dentista não consegue lançar evolução nem alterar o odontograma.
- Quem estava logado no sistema completo precisa entrar de novo, porque as chaves do token foram trocadas.
- O banco existente é atualizado sozinho na primeira inicialização. A alternativa manual é `database/migracao_4.0.1_seguranca.sql`.
- No Docker, o padrão agora sobe **sem** dados de demonstração. Para a demo, use `docker-compose.demo.yml`.

### Mudanças
- **B2:** o backend não inicia com segredo de exemplo ou fraco. O `.env` local recebeu chaves aleatórias de 64 caracteres, e a cópia anterior ficou em `.env.bak_antes_B2`.
- **B1:** o `seed_demo.sql` saiu do compose padrão e entrou o comando `flask --app wsgi definir-senha-admin`.
- **B7:** as portas do MySQL e da API não são mais publicadas. Entraram cabeçalhos de segurança no nginx e na API, e um modelo de HTTPS.
- **B3:** entraram logout no servidor, "sair de todos os dispositivos" e troca da própria senha. As sessões são encerradas ao trocar senha ou perfil e ao desativar o usuário.
- **B4/B5:** o dentista vê o CPF mascarado e não vê o endereço. A leitura de prontuário, odontograma e ficha é auditada.
- **B8:** as dependências foram atualizadas e o `pip-audit` não encontrou vulnerabilidades.
- **B9:** o profissional do registro clínico é o do usuário logado. Na tela de Prontuário, o campo fica travado para quem tem vínculo.
- **B6:** entraram o ProxyFix e o Redis para o limite de tentativas de login.
- **B10 a B14:** limite de upload de 10 MB, login sem enumeração de e-mail, política de senha, CPF mascarado no log mais um comando de retenção, e ajustes de CORS e da busca com LIKE.
- **Pendente:** MFA (autenticação em duas etapas).
- Os arquivos anteriores foram guardados em `backup_antes_seguranca_20261002/`.

## Versão 4.0 (01/10/2026)

### Odontograma anatômico 3D (Prontuário)
- Nova visualização das arcadas em vista oclusal, no formato real da boca:
  Maxila em cima, Mandíbula embaixo e lados direito e esquerdo do paciente indicados.
- Cada dente tem o formato do seu tipo (incisivo, canino, pré-molar ou molar),
  com volume, sombra e brilho; gengiva, palato e língua também são desenhados.
- Inclinação 3D suave ao mover o mouse, desativada automaticamente para quem
  usa a opção "reduzir movimento" do sistema operacional.
- Notação FDI colorida por grupo: incisivos (laranja), caninos (verde),
  pré-molares (roxo) e molares (azul).
- Painel lateral com nome completo do dente, estado, faces, atendimento e
  observação, além do botão **Editar dente**.
- Todos os recursos da versão anterior foram mantidos: 11 estados com as mesmas cores, faces
  (M, D, O, V, L), indicador de observação, marcação de dente com atendimento,
  dente ausente, dentição decídua (20 dentes) e o mesmo formulário de edição.
- O botão **Ver em grade** alterna para a visualização anterior.
- Acessível por teclado: Tab navega entre os dentes e Enter abre a edição.

### Agenda
- Agendamentos de demonstração do dia seguinte até 31/12/2026: de 4 a 6 por dia,
  de segunda a sábado (fechado aos domingos), sem conflito de horário por cadeira.
- Pacientes alternados em rodízio, com 7 tipos de atendimento.
- Profissional definido conforme a especialidade: tratamento de canal com a
  endodontista e manutenção de aparelho com o ortodontista.
- Atendimentos dos próximos 2 dias com status "Confirmado"; os demais, "Agendado".

### Acesso
- A tela de entrada passa a pedir login e senha (login `adminds`).
  A senha não consta na documentação; o arquivo armazena apenas o hash.

### Documentação
- README atualizado (novidades, acesso, notação FDI, uso em outro computador
  e local correto do `SISTEMA_CLINICA.html`).
- Novos `docs/ODONTOGRAMA.md` e `docs/Configuração do Sistema.pdf` (versão 4.0).
- Novo `LOG-01-10-2026.md`, com o registro das atividades do dia.
- Versão 4.0 exibida no menu lateral, na tela de acesso e no Dashboard.

### Correções após testes e auditoria de segurança
- Menu com **Usuários**; aviso de pedidos de senha pendentes ao entrar.
- Portal do paciente acessível pelo botão **Sou paciente: acessar o portal**.
- Pacientes: botão **Editar**; validação de CPF (11 dígitos e duplicidade) e de
  nascimento futuro; busca sem acento e por CPF só com números.
- Agenda: conflito pela duração do procedimento (cadeira e profissional), recusa
  de domingo, data passada e horário fora do expediente; **Receber** oculto para
  consultas canceladas e faltas; agenda de demonstração sem sobreposições.
- Portal: horários oferecidos e gravados respeitam a duração; cancelamento com
  confirmação e remoção do lançamento pendente.
- Prontuário: botão **+ Nova evolução**; histórico com as próximas 10 e as
  últimas 30 consultas.
- Financeiro: valor deve ser maior que zero.
- Modais: Esc fecha e o foco entra no modal; layout sem rolagem lateral no celular.
- Segurança: senha com PBKDF2-SHA-256; bloqueio após 5 tentativas na tela de
  acesso e no portal; senha de demonstração removida do HTML; mensagens que não
  revelam CPFs cadastrados; criação de conta exige a data de nascimento do
  cadastro; recuperação não reativa conta bloqueada; senha provisória com
  gerador criptográfico.
- Resultado final: 153 testes automatizados aprovados e nenhum XSS. Detalhes em
  `docs/TESTES_E_SEGURANCA_4.0.md`; roteiro em `tests/test_medflow_e2e.py`.

### Backup
- Versão anterior preservada em `SISTEMA_CLINICA_BACKUP_20261001.html`.

## Versões anteriores

- 30/09/2026: revisão de segurança (`docs/RELATORIO_SEGURANCA_MEDFLOW_2026-09-30.pdf`)
  e backup `SISTEMA_CLINICA_BACKUP_20260930.html`.
- 28/08/2026: organização da pasta e ajustes no site institucional e nos
  relatórios. Detalhes em `LOG-28-08-2026.md`.
