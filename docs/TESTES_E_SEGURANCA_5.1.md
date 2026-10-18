# Testes e segurança da versão 5.1

Data: 02/10/2026. Objeto: `SISTEMA_CLINICA.html` (versão 5.1) e código da versão completa (backend Flask, MySQL e trechos do frontend React).

## 1. Resultado

| Item | Resultado |
|---|---|
| Testes funcionais automatizados (E2E) | 172 casos, 172 aprovados, 0 reprovados |
| Erros de JavaScript durante os testes | Nenhum |
| XSS (injeção de script) nos campos digitáveis | Nenhum disparou |
| Segurança do `SISTEMA_CLINICA.html` | Adequada para uso local de demonstração, com riscos residuais descritos na seção 6 |
| Segurança do backend (versão completa) | Pendências B1 a B14 corrigidas na versão 4.0.1 e conferidas em 02/10/2026: 41 testes do backend e 17 testes independentes aprovados, `pip-audit` sem vulnerabilidades. Falta o MFA (seção 7) |

Nenhum teste garante ausência total de defeitos. Os resultados valem para os cenários descritos aqui, executados no Chromium.

## 2. Como os testes foram feitos

- **Testes funcionais:** suíte automatizada com Python e Playwright que abre o sistema no navegador e usa a interface como um usuário: clica, digita, salva e confere o resultado na tela e nos dados. O roteiro está em `tests/test_medflow_e2e.py`.
- **Segurança:** revisão do código-fonte com testes dinâmicos (tentativas de XSS em todos os campos, contorno da tela de acesso, enumeração de contas, força bruta, acesso de um paciente a dados de outro) e, no backend, testes com banco SQLite em memória e verificação de dependências com `pip-audit`.
- **Rodadas:** os defeitos encontrados foram corrigidos e o sistema foi testado novamente até não restar reprovação.

| Rodada | Casos | Aprovados | Reprovados |
|---|---|---|---|
| 1 (versão inicial 4.0) | 142 | 114 | 28 |
| 2 (após a 1ª correção) | 154 | 149 | 5 |
| 3 (versão final 4.0) | 153 | 153 | 0 |
| 4 (versão 5.0) | 172 | 172 | 0 |
| 5 (versão 5.1, testes finais) | 172 | 172 | 0 |

## 3. Cobertura dos testes automatizados

| Área | Casos | O que foi verificado |
|---|---|---|
| Carregamento e acesso | 14 | Carga sem erros, login correto e incorreto, Enter, maiúsculas, bloqueio após 5 tentativas, sair e entrar |
| Navegação e Dashboard | 10 | Todas as telas do menu, inclusive Usuários, e indicadores do Dashboard |
| Pacientes | 20 | Cadastro, campos obrigatórios, CPF (11 dígitos e duplicidade), nascimento futuro, edição, busca sem acento e por CPF |
| Agenda | 28 | Criação, conflito por duração (cadeira e profissional), domingo, data passada, expediente, status, recebimento; agenda de demonstração até 31/12/2026 |
| Prontuário e odontograma | 29 | 32 e 20 dentes na notação FDI, painel, edição, faces, observação, ausente, teclado, grade, impressão, nova evolução clínica |
| Financeiro, Estoque e Relatórios | 17 | Lançamentos (valor maior que zero), movimentação de estoque, abas e impressão dos relatórios |
| Usuários e portal do paciente | 24 | Acesso pelo botão da tela inicial, login, bloqueio, criação de conta, recuperação de senha, agendamento, cancelamento com confirmação |
| Responsividade | 10 | Telas em 1280 px e 375 px sem rolagem lateral; odontograma e modais cabem no celular |
| RH, comissões e contracheque (5.0) | 9 | Menu RH, comissão padrão de 25%, novo dentista na agenda, comissão acima de 100% recusada, comissão igual a 25% da produção paga, INSS e IRRF de referência, contracheque e impressão, folha lançada uma única vez, versão 5.0 no menu |
| Totais dos relatórios (5.0) | 10 | Quadro de totais coerente e linhas de total nos relatórios diário, semanal, mensal e anual; ganhos dos dentistas (bruto, descontos e líquido); comissões sem contagem dupla |
| Erros gerais | 1 | Nenhum erro de JavaScript em toda a execução |

## 4. Correções feitas durante os testes

**Funcionais**
- Menu passou a exibir **Usuários**; pedidos de senha pendentes geram aviso ao entrar.
- Portal do paciente acessível pelo botão **Sou paciente: acessar o portal** na tela de acesso.
- Pacientes: botão **Editar**, validação de CPF, CPF duplicado e nascimento futuro; data de nascimento não vem mais preenchida; busca ignora acentos.
- Agenda: conflito considera a duração do procedimento, na mesma cadeira e com o mesmo profissional; recusa domingo, data passada e horário fora do expediente; **Receber** não aparece para consultas canceladas ou faltas. A agenda de demonstração também respeita a duração.
- Portal: só oferece e grava horários realmente livres; cancelamento exige confirmação e remove o lançamento pendente.
- Prontuário: botão **+ Nova evolução**; histórico mostra as próximas 10 consultas e as últimas 30 realizadas.
- Odontograma: aviso quando há registro em dente da outra dentição.
- Financeiro: valor deve ser maior que zero.
- Modais: tecla Esc fecha e o foco entra no modal ao abrir.
- Layout: sem rolagem lateral em celular (375 px) e em 1280 px.

**Segurança**
- Senha de acesso protegida com PBKDF2-SHA-256 (150 mil iterações) no lugar do hash antigo, que admitia colisões.
- Bloqueio de 30 segundos após 5 tentativas erradas na tela de acesso e no portal do paciente.
- Senha de demonstração removida do HTML; senha do administrador unificada com a tela de acesso.
- Mensagens genéricas no login do portal, na criação de conta e na recuperação de senha, sem revelar quais CPFs estão cadastrados.
- Criação de conta com CPF já cadastrado exige a data de nascimento do cadastro.
- Recuperação de senha não reativa conta bloqueada.
- Senha provisória gerada com gerador criptográfico (`crypto.getRandomValues`).

## 5. Checklist de validação manual

Use antes de colocar uma nova versão em uso. Marque cada item ao conferir.

**Acesso**
- [ ] O sistema abre com dois cliques e mostra a tela de acesso com login e senha.
- [ ] Login `adminds` com a senha correta entra no Dashboard.
- [ ] Senha errada mostra "Login ou senha incorretos"; após 5 erros, aparece "Muitas tentativas".
- [ ] O menu lateral e a tela de acesso mostram "versão 5.1".
- [ ] **Sair** volta à tela de acesso.

**Pacientes**
- [ ] Cadastrar paciente com nome, CPF e data de nascimento.
- [ ] CPF com menos de 11 dígitos, CPF repetido e nascimento futuro são recusados.
- [ ] **Editar** abre os dados preenchidos e salva a alteração.
- [ ] A busca encontra "Patricia" (sem acento) e CPF digitado só com números.

**Agenda**
- [ ] Datas entre amanhã e 31/12/2026 têm de 4 a 6 atendimentos (exceto domingos).
- [ ] Novo agendamento em horário ocupado (mesma cadeira ou mesmo profissional) é recusado.
- [ ] Domingo, data passada e horário fora de 08:00 a 17:00 são recusados.
- [ ] **Receber** registra o pagamento e muda o status para Concluído.

**Prontuário e odontograma**
- [ ] O odontograma mostra as arcadas em 3D com números FDI (11 a 48).
- [ ] Ao passar o mouse, o painel lateral mostra nome, estado, faces e observação do dente.
- [ ] Clicar em um dente, marcar Cárie com faces e observação e salvar: o dente muda de cor e mostra as faces.
- [ ] **Decíduos (leite)** mostra 20 dentes (51 a 85); **Ver em grade** e **Ver arcada 3D** alternam a visualização.
- [ ] **+ Nova evolução** registra a evolução clínica e ela aparece na lista.
- [ ] **Imprimir** gera o relatório do odontograma.

**Financeiro, Estoque e Relatórios**
- [ ] Lançamento com valor zero ou negativo é recusado; lançamento válido atualiza os totais.
- [ ] Entrada e saída de estoque atualizam o saldo; saída maior que o saldo é recusada.
- [ ] As abas de Relatórios abrem e imprimem.

**RH, comissões e contracheque (5.0)**
- [ ] **RH** aparece no menu e lista os 3 dentistas (25%) e os 3 funcionários CLT.
- [ ] Novo colaborador Dentista é salvo e aparece na lista de profissionais da Agenda.
- [ ] Comissão acima de 100% e admissão futura são recusadas.
- [ ] Em **Comissões e folha**, a comissão de cada dentista é 25% da produção paga do mês.
- [ ] **Lançar folha no Financeiro** cria as despesas; um segundo clique não duplica.
- [ ] **Contracheque** abre com proventos, INSS, IRRF e valor líquido e imprime.
- [ ] **Imprimir todos os contracheques** gera um contracheque por colaborador.

**Totais dos relatórios (5.0)**
- [ ] Relatórios diário, semanal, mensal e anual mostram **Totais do período**.
- [ ] Resultado líquido = Recebido − Despesas − Comissões.
- [ ] Tabela de comissões por dentista termina com a linha TOTAL.
- [ ] Gráficos mostram a linha de total.
- [ ] **Ganhos dos dentistas** mostra comissão bruta, descontos e líquida, com total geral.

**Usuários e portal do paciente**
- [ ] **Usuários** aparece no menu e lista os pedidos de senha.
- [ ] Na tela de acesso, **Sou paciente: acessar o portal** abre o login do paciente.
- [ ] Paciente entra com CPF e data de nascimento (ddmmaaaa), agenda uma consulta e a vê em "Minhas consultas".
- [ ] Cancelar consulta pede confirmação.

**Celular**
- [ ] Em tela de celular, o menu quebra em linhas, não há rolagem lateral e o odontograma cabe na tela.

## 6. Segurança do SISTEMA_CLINICA.html

| ID | Achado | Situação |
|---|---|---|
| A1 | Tela de acesso | Corrigido em parte. Hash forte e bloqueio de tentativas aplicados. Permanece o que é inerente a um arquivo local: o bloqueio zera ao recarregar a página e quem tem o arquivo pode abri-lo pelo console do navegador. Use senha longa (10 ou mais caracteres) e não deixe o arquivo em computador compartilhado. |
| A2 | Criação de conta no portal | Corrigido em parte. Sem a data de nascimento correta não é possível criar conta. Quem conhece CPF e data de nascimento de um paciente consegue criar a conta dele; numa versão com servidor, é preciso confirmação por e-mail ou SMS. |
| A3 | Recuperação de senha e login do paciente | Corrigido. Mensagens genéricas e bloqueio de tentativas. A senha inicial do paciente continua sendo a data de nascimento, por regra do sistema. |
| A4 | Senha do administrador duplicada | Corrigido. |
| A5 | Senhas de pacientes em texto na memória | Pendente, de baixo risco nesta versão (os dados existem só enquanto a página está aberta). Numa versão com banco, usar hash bcrypt ou argon2. |
| A6 | Portal e tela de usuários sem acesso | Corrigido. |

XSS: testado com cargas maliciosas em todos os campos digitáveis (pacientes, evolução clínica, odontograma, financeiro, estoque, cadastros e portal). Nenhuma foi executada; o sistema exibe o conteúdo como texto.

## 7. Pendências do backend antes de produção

As pendências B1 a B14 do relatório da versão 4.0 foram corrigidas na versão 4.0.1 (02/10/2026). O detalhamento está em `docs/SECURITY.md`.

| ID | Severidade | Situação em 02/10/2026 |
|---|---|---|
| B1 | Alta | Corrigido. Dados de demonstração fora do `docker-compose.yml` padrão; comando `definir-senha-admin`. |
| B2 | Alta | Corrigido. O backend não inicia com `SECRET_KEY` ou `JWT_SECRET_KEY` fracos, de exemplo ou iguais. |
| B3 | Média | Corrigido. Logout com revogação; sessões encerradas ao trocar senha ou perfil e ao desativar o usuário. |
| B4, B5 | Média | Corrigido. CPF mascarado e sem endereço para o dentista; leitura de prontuário auditada. |
| B6 | Média | Corrigido. ProxyFix e Redis para o limite de tentativas de login. |
| B7 | Média | Corrigido. Portas 3306 e 5000 não publicadas; cabeçalhos de segurança; modelo de HTTPS. |
| B8 | Média | Corrigido. Dependências atualizadas; `pip-audit` sem vulnerabilidades conhecidas. |
| B9 | Média | Corrigido. O profissional do registro clínico é o do usuário logado. |
| B10 a B14 | Baixa | Corrigidos, exceto o MFA (parte do B12), que ainda não foi implementado. |

Antes de publicar: configurar HTTPS com certificado real, definir a senha do administrador com `definir-senha-admin`, ativar o Redis e o backup do MySQL e avaliar o MFA para administradores.

## 8. Limitações

- Testes executados apenas no Chromium (Chrome e Edge usam o mesmo motor); Firefox e Safari não foram testados.
- A impressão foi verificada pelo conteúdo gerado, sem imprimir em papel ou PDF.
- Na versão 5.0, comissões, totais e resultado líquido foram recalculados de forma independente nos testes. O relatório de IR continua conferido apenas quanto à exibição.
- INSS e IRRF foram conferidos com valores de referência das tabelas de 2026. O contracheque não substitui a folha oficial do contador e não trata dependentes, férias, 13º e horas extras.
- Alguns casos automatizados usam datas fixas de outubro de 2026 e precisarão de ajuste depois desse mês.
- O backend foi testado com SQLite em memória, sem MySQL, gunicorn e nginx reais; não houve teste de infraestrutura, backup ou análise jurídica de LGPD.

## 9. Como executar os testes automatizados

```
pip install playwright
python -m playwright install chromium
set MEDFLOW_ADMIN_PASS=<senha do administrador>
python tests/test_medflow_e2e.py
```

No Linux ou macOS, use `export MEDFLOW_ADMIN_PASS=<senha do administrador>`. O resultado aparece no terminal (`TOTAL`, `PASSOU`, `FALHOU`) e fica salvo em `tests/resultados/`.

## 10. Testes finais de 02/10/2026 (versão 5.1)

Executados depois de concluídas as correções de segurança do backend (versão 4.0.1) e o módulo de RH (versão 5.0).

| Teste | Resultado |
|---|---|
| Sistema da clínica (`tests/test_medflow_e2e.py`) | 172 casos, 172 aprovados, sem erros de JavaScript |
| Segurança do backend (`tests/test_backend_seguranca.py`) | 41 casos, 41 aprovados |
| Testes independentes de ataque ao backend (`tests/test_backend_independente.py`) | 17 casos, 17 aprovados |
| Dependências (`pip-audit -r backend/requirements.txt`) | Nenhuma vulnerabilidade conhecida |

Os testes independentes foram escritos por quem não fez as correções e cobriram:

- token sem assinatura (`alg: none`), token de renovação usado como token de acesso e acesso sem token;
- perfis sem permissão tentando listar, criar ou alterar usuários e ler prontuário ou odontograma;
- usuário desativado tentando entrar;
- injeção de SQL e curingas (`%`, `_`) na busca de pacientes;
- texto com script salvo e devolvido como JSON, com o cabeçalho `nosniff`;
- força bruta com vários e-mails a partir do mesmo IP (bloqueio por excesso de tentativas, HTTP 429);
- JSON malformado sem expor detalhes internos;
- `docker-compose.yml` sem as portas 3306 e 5000 publicadas e sem o `seed_demo.sql`.

Observação: o usuário desativado recebe "Usuário inativo" (HTTP 403) somente depois de informar a senha correta. Com senha errada, a resposta é a mesma de qualquer outra tentativa, o que não permite descobrir quais contas existem.
