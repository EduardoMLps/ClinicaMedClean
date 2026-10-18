# Segurança do backend: resumo em linguagem simples

Documento destinado ao professor ou analista responsável pelo projeto. Explica,
sem jargão técnico excessivo, o que foi revisado, o que foi corrigido e o que
ainda falta para que o sistema possa ser usado com pacientes reais.

Data da revisão: 17/08/2026.
Escopo revisado: `backend/app/models`, `backend/app/routes`, `backend/app/utils`,
`backend/app/config.py`, `backend/app/__init__.py` e `backend/app/extensions.py`.

## O que foi encontrado e corrigido nesta revisão

### 1. Prontuário e odontograma podiam ser lidos por qualquer usuário logado

**Problema:** para consultar o prontuário (histórico clínico, diagnósticos e
anotações do dentista) ou o odontograma (mapa dos dentes) de um paciente,
bastava estar logado no sistema, independentemente do cargo da pessoa.
Assim, um usuário da recepção ou do financeiro, ou até um dentista
sem nenhuma relação com o paciente, conseguia ver o histórico clínico
completo de qualquer paciente apenas trocando o número do paciente no
endereço web (ex.: `/prontuarios/1`, `/prontuarios/2`, `/prontuarios/3`...).

**Gravidade:** dados clínicos (diagnósticos, evoluções e
tratamentos) são informações sensíveis de saúde, protegidas pela LGPD.
O vazamento ou o acesso indevido a esse tipo de dado está entre os riscos mais sérios
de um sistema de clínica.

**Correção aplicada:** as rotas `GET /api/v1/prontuarios/<paciente_id>` e
`GET /api/v1/odontograma/<paciente_id>` agora exigem, além do login,
que o usuário tenha o perfil de administrador ou dentista, os
mesmos perfis que já eram exigidos para gravar esses dados. Perfis
como recepção e financeiro deixam de ter acesso de leitura ao prontuário e ao odontograma.
A correção foi validada com teste automatizado: um usuário com perfil de recepção agora
recebe "acesso negado" (código 403) ao acessar essas duas rotas.

Arquivo alterado: `backend/app/routes/clinico.py`.

*Observação:* essa correção resolve o vazamento entre perfis (recepção
vendo prontuário), mas ainda não resolve o caso de um dentista sem
vínculo com determinado paciente conseguir ler o prontuário dele.
Para isso, seria necessário verificar se existe uma relação profissional-paciente
(por exemplo, um atendimento ou agendamento entre os dois) antes de liberar a leitura.
Essa melhoria de regra de negócio é recomendada para uma próxima etapa e não
foi implementada agora para não travar o funcionamento normal da clínica,
já que qualquer dentista pode precisar atender qualquer paciente.

### 2. Login sem limite de tentativas (força bruta)

**Problema:** a rota de login (`POST /api/v1/auth/login`) aceitava
um número ilimitado de tentativas de senha.
Um programa automatizado poderia testar milhares de senhas por minuto contra
qualquer e-mail cadastrado até acertar (ataque de força bruta).

**Correção aplicada:** foi ativado o Flask-Limiter, biblioteca que já
constava nas dependências do projeto, mas que nunca havia sido de fato
integrada à aplicação. Agora:
- O limite é de 5 tentativas de login por minuto para a combinação
  IP + e-mail, o que impede que um atacante insista em senhas contra um
  e-mail específico.
- O limite total é de 20 tentativas de login por minuto por IP, o que impede
  que um único atacante percorra rapidamente vários e-mails diferentes
  a partir do mesmo IP.
- Ao ultrapassar o limite, a API responde com o código HTTP 429 (Too Many
  Requests) em vez de processar a tentativa de senha.

A correção foi validada com teste automatizado: a 6ª tentativa consecutiva de login
recebe 429 em vez de ser processada.

Arquivos alterados: `backend/app/extensions.py` (criação do limiter),
`backend/app/__init__.py` (ativação do limiter na aplicação) e
`backend/app/routes/auth.py` (limite aplicado à rota de login).

*Observação sobre produção:* o armazenamento padrão da contagem de tentativas
(`RATELIMIT_STORAGE_URI=memory://`) mantém os contadores apenas na
memória de um processo. Isso funciona bem em desenvolvimento e em um
único servidor. Porém, se o sistema rodar com vários processos ou servidores ao
mesmo tempo (comum em produção), cada processo terá sua própria contagem, o
que enfraquece o limite. Antes de um deploy real, essa variável deve
apontar para um Redis compartilhado (ex.:
`RATELIMIT_STORAGE_URI=redis://...`), conforme já comentado no
`.env.example`.

## O que já estava correto (verificado, sem necessidade de correção)

- Todas as rotas de escrita (criar, editar e excluir) já exigiam login
  válido e perfil autorizado. Não foi encontrada nenhuma rota de escrita
  desprotegida.
- Nenhuma consulta ao banco de dados é montada por concatenação de texto,
  o que causaria risco de SQL injection; as poucas consultas em SQL
  puro usam parâmetros nomeados corretamente.
- Senhas nunca são armazenadas nem exibidas em texto puro: usam o algoritmo
  bcrypt (padrão de mercado) e são explicitamente removidas de qualquer
  resposta da API e dos registros de auditoria.
- O upload de exames e anexos já valida o tipo de arquivo, o tamanho máximo
  (10 MB) e o conteúdo real do arquivo (não apenas a extensão do nome),
  o que reduz o risco de upload de arquivos maliciosos disfarçados.
- Nenhuma senha de banco de dados ou chave secreta está escrita diretamente no
  código-fonte. Tudo vem de variáveis de ambiente (arquivo `.env`, que não
  deve ser enviado ao Git), e a aplicação se recusa a iniciar caso as
  chaves obrigatórias (`SECRET_KEY` e `JWT_SECRET_KEY`) não sejam
  fornecidas.
- O token de acesso (o "crachá digital" que comprova que
  o usuário está logado) já estava configurado para expirar em 30 minutos
  por padrão, o que evita que um token roubado continue válido por muito
  tempo.
- O CORS (regra que define quais sites podem chamar a API pelo navegador) já
  estava restrito ao endereço configurado em `FRONTEND_URL`, sem
  liberação para qualquer site (`*`).

## Recomendações antes de um deploy real com pacientes

Agora o projeto tem uma base de segurança razoável para fins
acadêmicos e de demonstração. Antes de usá-lo com dados reais de pacientes,
recomenda-se:

1. **Revisão por um profissional de segurança.** Esta correção foi
   feita por um agente de IA a partir de um checklist específico e não
   substitui uma auditoria de segurança feita por uma pessoa especializada,
   capaz de avaliar riscos de contexto e de negócio que um checklist
   não cobre.
2. **Teste de invasão (pentest)** realizado por terceiros antes de abrir o
   sistema para uso com pacientes reais, incluindo testes da API,
   do frontend e da infraestrutura (servidor, banco de dados e backups).
3. **Certificado SSL/TLS válido (HTTPS)** em produção. O projeto
   pressupõe que haja HTTPS na frente da aplicação (ex.: via proxy ou load
   balancer), pois o Flask sozinho não fornece isso. Sem HTTPS, mesmo com um
   login bem protegido, senhas e tokens trafegam sem criptografia e podem
   ser interceptados na rede.
4. **Backups efetivamente testados.** Não basta configurar o backup automático
   do banco de dados: é preciso testar periodicamente a restauração
   e a recuperação correta dos dados. Um backup que
   nunca foi restaurado em teste não é confiável.
5. **Redis (ou similar) para o rate limiting em produção**, conforme
   comentado acima, se o sistema for executado com mais de um processo ou servidor.
6. **Definição e implementação do controle de vínculo profissional-paciente**
   para leitura de prontuário e odontograma (veja a observação do item 1 acima),
   caso a política da clínica exija que apenas os dentistas responsáveis
   por um paciente vejam o prontuário dele.
7. **Política de senhas e MFA (autenticação em duas etapas)** para as contas
   de administrador, já que esse perfil tem amplo acesso a
   dados clínicos e financeiros.
8. **Monitoramento e alertas** de tentativas de login malsucedidas em
   volume anormal, mesmo com o rate limiting em vigor, para detectar
   ataques em andamento.
9. **Adequação formal à LGPD:** política de privacidade, termo de
   consentimento dos pacientes, definição do prazo de retenção dos dados
   e processo formal para atender a pedidos de exclusão e portabilidade de
   dados dos titulares.

## Resumo

| Item | Situação antes | Situação depois |
|---|---|---|
| Leitura de prontuário/odontograma | Qualquer usuário logado | Apenas administrador e dentista |
| Tentativas de login | Ilimitadas | 5/min por IP+e-mail, 20/min por IP |
| Senha em texto puro | Não ocorria | Continua não ocorrendo |
| SQL injection | Não encontrado | Continua não encontrado |
| Segredos no código | Não encontrado (já via `.env`) | Continua via `.env` |
| Expiração do token | 30 min (já configurado) | Mantida em 30 min |
| CORS aberto para qualquer site | Não ocorria | Continua restrito a `FRONTEND_URL` |

---

## Versão 4.0.1 (02/10/2026): pendências B1 a B14

Esta etapa fechou as pendências listadas em `TESTES_E_SEGURANCA_4.0.md`. Cada item tem teste automatizado em `tests/test_backend_seguranca.py`, com 41 testes, todos passando.

### Infraestrutura

- **B2: segredos fracos.** O backend não inicia se `SECRET_KEY` ou `JWT_SECRET_KEY` tiverem menos de 32 caracteres, parecerem valor de exemplo (`TROCAR_ESTE_VALOR`, `change-me`...), tiverem pouca variedade de caracteres ou forem iguais entre si.
- **B1: senha de demonstração.** O `docker-compose.yml` padrão sobe sem o `seed_demo.sql`. Os dados fictícios ficam no `docker-compose.demo.yml`, que só entra se for pedido explicitamente. Para definir a senha real do administrador, use:
  `docker compose exec backend flask --app wsgi definir-senha-admin`
- **B7: portas, HTTPS e cabeçalhos.** O MySQL (3306), a API (5000) e o Redis não são mais publicados, ficando só na rede interna do Docker. O nginx envia CSP, `X-Frame-Options`, `nosniff`, `Referrer-Policy` e `Permissions-Policy`, e as respostas da API vão com `Cache-Control: no-store`. O arquivo `frontend/nginx-https.conf.exemplo` traz o HTTPS pronto (TLS 1.2/1.3, redirecionamento e HSTS), bastando colocar o certificado.
- **B6: limite de tentativas atrás do nginx.** O `ProxyFix` passa a ler o IP real quando `TRUSTED_PROXY_COUNT=1`. O nginx sobrescreve o `X-Forwarded-For`, então o cliente não consegue forjá-lo. Os contadores ficam no Redis do compose, compartilhados entre os workers do gunicorn.
- **B8: dependências.** Foram atualizadas Flask 3.1.3, Flask-CORS 6.0.5, cryptography 50.0.2, python-dotenv 1.2.4, gunicorn 26.2.0 e outras. O `pip-audit` não encontrou vulnerabilidades conhecidas em 02/10/2026. Rode `pip-audit -r backend/requirements.txt` a cada nova versão.

### Sessão e acesso

- **B3: revogação de token.** Há três rotas novas: `POST /api/v1/auth/logout`, que revoga o token e o refresh, `POST /api/v1/auth/logout-todos` e `POST /api/v1/auth/alterar-senha`. Os tokens antigos deixam de valer quando o usuário troca de senha, troca de perfil ou é desativado. A cada requisição o sistema confere no banco se o usuário existe, se está ativo e se o perfil é o mesmo do token. O botão **Sair** do frontend agora avisa o servidor.
- **B4: dados pessoais por perfil.** Administrador, recepção e financeiro veem o CPF completo e o endereço. O dentista vê nome, idade e contato, mas recebe o CPF mascarado (`***.456.789-**`) e não recebe o endereço.
- **B5: auditoria de leitura (LGPD).** Abrir o prontuário, o odontograma ou a ficha completa de um paciente gera um registro `acao='ler'` em `log_auditoria`, com o usuário e o horário.
- **B9: profissional do registro clínico.** O usuário agora pode ser vinculado a um profissional pelo campo `profissional_id`, em Usuários. A evolução, o prontuário e o odontograma saem sempre em nome do profissional vinculado, e o sistema recusa outro (403). O administrador sem vínculo pode registrar informando o profissional, e o registro fica na auditoria em nome dele.
  **Ação necessária:** vincule cada usuário dentista ao seu cadastro de profissional (`PUT /api/v1/usuarios/<id>` com `{"profissional_id": N}`). Dentista sem vínculo não consegue lançar registros clínicos.

### Ajustes menores

- **B10:** o limite de requisição e upload é de 10 MB (`MAX_UPLOAD_MB`), aplicado no Flask e no nginx, com mensagem clara (413).
- **B11:** o login com e-mail inexistente leva o mesmo tempo e dá a mesma resposta que um e-mail existente com senha errada.
- **B12:** a política de senha para novos usuários e para trocas exige no mínimo 10 caracteres, letras e números, sem senhas comuns e sem conter o nome ou o e-mail. **Pendente: MFA** (autenticação em duas etapas). Ele exige telas novas no frontend e não foi feito nesta etapa. Continua recomendado para o perfil administrador.
- **B13:** o log de auditoria guarda o CPF sempre mascarado. O comando `flask --app wsgi limpar-logs-auditoria` remove registros mais antigos que `AUDIT_LOG_RETENCAO_DIAS` (padrão de 1825 dias, ou 5 anos). O prazo deve ser confirmado com orientação jurídica.
- **B14:** o CORS não libera mais credenciais de navegador e aceita só os métodos e cabeçalhos usados. Nas buscas, `%` e `_` digitados pelo usuário são tratados como texto, não como curinga.

### Bancos já existentes

Ao iniciar, o backend cria sozinho as tabelas novas (`tokens_revogados` e `revogacoes_sessao_usuario`) e a coluna `usuarios.profissional_id`. Se o usuário do banco não tiver permissão para isso, rode `database/migracao_4.0.1_seguranca.sql` como root.

### Ainda recomendado antes de produção

Continuam valendo os itens da seção "Recomendações antes de um deploy real com pacientes" acima: revisão humana, pentest, backups testados, MFA, monitoramento e a adequação formal à LGPD.
