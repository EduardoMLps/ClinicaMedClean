# Testes e segurança da versão 4.0

Data: 01/10/2026. Objeto: `SISTEMA_CLINICA.html` (versão 4.0) e código da versão completa (backend Flask, MySQL e trechos do frontend React).

## 1. Resultado

| Item | Resultado |
|---|---|
| Testes funcionais automatizados (E2E) | 153 casos, 153 aprovados, 0 reprovados |
| Erros de JavaScript durante os testes | Nenhum |
| XSS (injeção de script) nos campos digitáveis | Nenhum disparou |
| Segurança do `SISTEMA_CLINICA.html` | Adequada para uso local de demonstração, com riscos residuais descritos na seção 6 |
| Segurança do backend (versão completa) | Não liberado para produção: há 2 achados de severidade alta e 7 de severidade média pendentes (seção 7) |

Nenhum teste garante ausência total de defeitos. Os resultados valem para os cenários descritos aqui, executados no Chromium.

## 2. Como os testes foram feitos

- **Testes funcionais:** suíte automatizada com Python e Playwright que abre o sistema no navegador e usa a interface como um usuário: clica, digita, salva e confere o resultado na tela e nos dados. O roteiro está em `tests/test_medflow_e2e.py`.
- **Segurança:** revisão do código-fonte com testes dinâmicos (tentativas de XSS em todos os campos, contorno da tela de acesso, enumeração de contas, força bruta, acesso de um paciente a dados de outro) e, no backend, testes com banco SQLite em memória e verificação de dependências com `pip-audit`.
- **Rodadas:** os defeitos encontrados foram corrigidos e o sistema foi testado novamente até não restar reprovação.

| Rodada | Casos | Aprovados | Reprovados |
|---|---|---|---|
| 1 (versão inicial 4.0) | 142 | 114 | 28 |
| 2 (após a 1ª correção) | 154 | 149 | 5 |
| 3 (versão final) | 153 | 153 | 0 |

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
- [ ] O menu lateral e a tela de acesso mostram "versão 4.0".
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

**Atualização de 02/10/2026 (versão 4.0.1):** as pendências B1 a B14 foram tratadas no código e cobertas por 41 testes automatizados em `tests/test_backend_seguranca.py`. Todos passam. O detalhamento está em `docs/SECURITY.md`, na seção "Versão 4.0.1".

| ID | Severidade | Situação |
|---|---|---|
| B2 | Alta | Corrigido. O backend não inicia com segredo de exemplo, curto, repetitivo ou com as duas chaves iguais. |
| B1 | Alta | Corrigido. Os dados de demonstração saíram do `docker-compose.yml`, foram para o `docker-compose.demo.yml`, e há o comando `definir-senha-admin`. |
| B7 | Média | Corrigido. As portas 3306 e 5000 não são mais publicadas. Há cabeçalhos de segurança no nginx e na API, e um modelo de HTTPS em `frontend/nginx-https.conf.exemplo`. |
| B3 | Média | Corrigido. Há logout com revogação do token, e as sessões são encerradas ao trocar senha ou perfil e ao desativar o usuário. A cada requisição, o sistema confere no banco se o usuário está ativo e qual é o perfil dele. |
| B4, B5 | Média | Corrigido. O dentista vê o CPF mascarado e não vê o endereço. A leitura de prontuário, odontograma e ficha do paciente é registrada na auditoria. |
| B8 | Média | Corrigido. As dependências foram atualizadas e o `pip-audit` não encontrou vulnerabilidades conhecidas em 02/10/2026. |
| B9 | Média | Corrigido. O profissional dos registros clínicos é o vinculado ao usuário logado. |
| B6 | Média | Corrigido. Entraram o ProxyFix (IP real atrás do nginx) e o Redis no compose para o limite de tentativas. |
| B10 a B14 | Baixa | B10, B11, B13 e B14 foram corrigidos. O B12 foi corrigido em parte: entrou a política de senha, mas o **MFA ainda não foi implementado** (veja a recomendação em `SECURITY.md`). |

Itens verificados e corretos no backend: controle de acesso ao prontuário por perfil, limite de tentativas de login por e-mail, JWT com expiração de 30 minutos e rejeição de tokens adulterados, consultas SQL parametrizadas, senhas com bcrypt, erros sem detalhes internos, token guardado só na memória no frontend e container sem usuário root.

## 8. Limitações

- Testes executados apenas no Chromium (Chrome e Edge usam o mesmo motor); Firefox e Safari não foram testados.
- A impressão foi verificada pelo conteúdo gerado, sem imprimir em papel ou PDF.
- Os valores dos relatórios mensal, anual e de IR foram conferidos quanto à exibição, não recalculados de forma independente.
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
