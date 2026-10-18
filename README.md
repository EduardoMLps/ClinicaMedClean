# Med Flow: Sistema de Gestão para Clínica Odontológica

**Versão atual: 5.1** (02/10/2026). O histórico completo está em [`CHANGELOG.md`](CHANGELOG.md).

Sistema web de gestão administrativa e clínica para clínica odontológica:
cadastro de pacientes, agenda de consultas, prontuário e odontograma,
controle financeiro e controle de estoque, com autenticação por usuário e
perfis de acesso (administrador, dentista, recepção e financeiro).

O sistema é composto por três partes, que rodam de forma independente e se
comunicam por API:

- Backend: API REST em Python (Flask), com autenticação via JWT.
- Frontend: aplicação web em React (Vite + Tailwind CSS).
- Banco de dados: MySQL 8, com o schema aplicado automaticamente na
  primeira inicialização.

> **Status do projeto:** protótipo funcional para fins de estudo e avaliação
> acadêmica. Antes de usar com pacientes e dados reais, leia a seção
> [Aviso importante sobre segurança](#aviso-importante-sobre-segurança-e-usuário-administrador-padrão)
> e o documento [`docs/SECURITY.md`](docs/SECURITY.md).

---

## Novidades da versão 5.1

A versão 5.1 reúne em uma única entrega o módulo de RH da versão 5.0 e as
correções de segurança do backend feitas na versão 4.0.1, conferidas nos testes
finais de 02/10/2026:

- Pendências de segurança do backend B1 a B14 corrigidas (detalhes em
  [`docs/SECURITY.md`](docs/SECURITY.md)). Continua pendente o MFA
  (autenticação em dois fatores).
- Testes finais: 172 de 172 no `SISTEMA_CLINICA.html`, 41 de 41 em
  `tests/test_backend_seguranca.py`, 17 de 17 em
  `tests/test_backend_independente.py` e `pip-audit` sem vulnerabilidades.
- Versão 5.1 exibida no menu lateral, na tela de acesso e no Dashboard.

Resultados e checklist em
[`docs/TESTES_E_SEGURANCA_5.1.md`](docs/TESTES_E_SEGURANCA_5.1.md).

---

## Novidades da versão 5.0

Mudanças feitas no `SISTEMA_CLINICA.html` (sistema de uso diário):

- Novo módulo **RH**: cadastro de colaboradores (dentistas e funcionários CLT),
  com cargo, vínculo, salário e percentual de comissão.
- Comissão dos dentistas: 25% do valor dos atendimentos concluídos e pagos. O
  percentual padrão pode ser alterado, e cada dentista pode ter o seu.
- Todos os relatórios (diário, semanal, mensal e anual) mostram o quadro
  **Totais do período** com recebido, despesas, comissões e resultado líquido,
  além da soma de todos os dentistas e linhas de total nos gráficos e tabelas.
- Nova aba **Ganhos dos dentistas** em Relatórios: valor total e líquido da
  comissão de cada dentista e do conjunto.
- **Contracheque** de cada colaborador, com INSS, IRRF (tabelas de 2026) e
  FGTS, pronto para imprimir. Os valores são de referência e devem ser
  conferidos pelo contador.
- Lançamento da folha (salários e comissões) no Financeiro com um clique.

Regras de cálculo em [`docs/RH_E_COMISSOES.md`](docs/RH_E_COMISSOES.md).

**Testes:** 172 casos automatizados aprovados, sem XSS e sem erros de JavaScript.
Checklist e resultados em
[`docs/TESTES_E_SEGURANCA_5.0.md`](docs/TESTES_E_SEGURANCA_5.0.md).

---

## Novidades da versão 4.0

Mudanças feitas no `SISTEMA_CLINICA.html` (sistema de uso diário):

- Odontograma anatômico 3D na tela de Prontuário. As arcadas aparecem como
  na boca do paciente (vista oclusal), com a Maxila em cima, a Mandíbula embaixo e
  a indicação dos lados direito e esquerdo do paciente. Cada dente tem o formato do seu
  tipo (incisivo, canino, pré-molar ou molar), com volume e sombra, e a arcada inclina
  levemente ao mover o mouse. Um painel lateral mostra o nome completo do dente,
  o estado, as faces, o atendimento e a observação. Todas as informações da versão
  anterior foram mantidas, e o botão **Ver em grade** volta à visualização antiga.
  Detalhes em [`docs/ODONTOGRAMA.md`](docs/ODONTOGRAMA.md).
- Notação FDI (dois dígitos) explicada no sistema e na documentação. É o
  padrão usado no Brasil (norma ISO 3950).
- Agenda de demonstração até 31/12/2026, com 4 a 6 atendimentos por dia, de
  segunda a sábado, alternando os pacientes, os 7 procedimentos e os
  profissionais conforme a especialidade.
- Tela de acesso com login e senha (antes pedia apenas a senha), protegida com
  PBKDF2 e bloqueio após 5 tentativas erradas.
- Portal do paciente acessível pelo botão **Sou paciente: acessar o portal**.
- Edição de pacientes, registro de nova evolução clínica e validações de CPF,
  datas, horários e valores.
- Versão 4.0 exibida no menu lateral, na tela de acesso e no Dashboard.

**Testes:** 153 casos automatizados aprovados, sem XSS e sem erros de JavaScript.
Checklist de validação, resultados e pendências de segurança em
[`docs/TESTES_E_SEGURANCA_4.0.md`](docs/TESTES_E_SEGURANCA_4.0.md).

---

## Acesso ao SISTEMA_CLINICA.html

- **Login:** `adminds`
- **Senha:** definida pelo administrador em 01/10/2026. Por segurança, ela
  não consta nesta documentação; guarde-a em local seguro. O arquivo
  armazena apenas uma versão embaralhada (hash) da senha.

Os arquivos `SISTEMA_CLINICA_BACKUP_*.html` são cópias de segurança de versões
anteriores e ainda usam a tela de acesso antiga. No dia a dia, use sempre
o `SISTEMA_CLINICA.html`.

---

## Numeração dos dentes (FDI)

O odontograma usa a notação FDI, padrão internacional (ISO 3950) adotado
no Brasil. O adulto tem 32 dentes, e cada um recebe dois dígitos:

| 1º dígito (quadrante) | Região (lado do paciente) | Dentes |
|---|---|---|
| 1 | Superior direito | 11 a 18 |
| 2 | Superior esquerdo | 21 a 28 |
| 3 | Inferior esquerdo | 31 a 38 |
| 4 | Inferior direito | 41 a 48 |

O 2º dígito indica a posição, do meio da boca para o fundo: 1, incisivo central;
2, incisivo lateral; 3, canino; 4 e 5, pré-molares; 6, 7 e 8, molares (8 = siso).
Exemplo: 16 = primeiro molar superior direito.

Os dentes de leite (decíduos) usam os quadrantes 5 a 8 e as posições de 1 a 5
(ex.: 51 = incisivo central superior direito de leite).

A numeração de 1 a 32 (Sistema Universal) é usada principalmente nos EUA, e o
número não indica a região do dente. Por isso, ela não é usada aqui.

---

## Estrutura de pastas

```
sistema-clinica/
├── backend/                   # API REST em Flask
│   ├── app/
│   │   ├── __init__.py        # application factory (cria e configura o Flask app)
│   │   ├── config.py          # leitura das variáveis de ambiente / configuração
│   │   ├── extensions.py      # inicialização de SQLAlchemy, JWT, CORS, rate limiter
│   │   ├── models/            # modelos de dados (SQLAlchemy)
│   │   │   ├── auth.py        # usuários, perfis, permissões
│   │   │   ├── pacientes.py   # pacientes
│   │   │   ├── clinico.py     # prontuário, odontograma, agendamentos clínicos
│   │   │   ├── financeiro.py  # lançamentos financeiros, pagamentos
│   │   │   └── estoque.py     # itens e movimentações de estoque
│   │   ├── routes/            # endpoints da API, um arquivo por módulo
│   │   │   ├── auth.py            # login, refresh token
│   │   │   ├── usuarios.py        # gestão de usuários e perfis
│   │   │   ├── pacientes.py       # CRUD de pacientes
│   │   │   ├── agenda.py          # agendamento de consultas
│   │   │   ├── clinico.py         # prontuário e odontograma
│   │   │   ├── financeiro.py      # contas a pagar/receber, pagamentos
│   │   │   ├── estoque.py         # controle de estoque
│   │   │   └── relatorios.py      # relatórios e indicadores
│   │   └── utils/
│   │       ├── auth_decorators.py # decorators de autorização por perfil
│   │       ├── security.py        # hashing de senha, helpers de segurança
│   │       └── notificacoes.py    # utilitários de notificação
│   ├── requirements.txt       # dependências Python
│   ├── wsgi.py                 # ponto de entrada usado pelo gunicorn
│   └── Dockerfile
│
├── frontend/                   # aplicação React
│   ├── src/
│   │   ├── main.jsx             # ponto de entrada da aplicação
│   │   ├── App.jsx              # definição de rotas
│   │   ├── api/client.js        # cliente HTTP (axios/fetch) para a API
│   │   ├── context/AuthContext.jsx  # estado de autenticação/sessão
│   │   ├── components/Layout.jsx    # layout comum (menu, cabeçalho)
│   │   ├── assets/               # logo, ícones, ilustrações
│   │   └── pages/                 # telas da aplicação (ver seção abaixo)
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── vite.config.js
│   ├── nginx.conf              # configuração usada para servir o build em produção
│   └── Dockerfile
│
├── database/
│   ├── schema.sql              # criação de todas as tabelas + usuário admin inicial
│   └── seed_demo.sql           # dados de exemplo opcionais para demonstração/testes
│
├── docs/
│   ├── SECURITY.md             # revisão de segurança do backend (leitura obrigatória)
│   ├── ODONTOGRAMA.md          # guia do odontograma 3D e da numeração FDI (v4.0)
│   ├── Configuração do Sistema.pdf  # como instalar/abrir em outro computador (v4.0)
│   ├── TESTES_E_SEGURANCA_4.0.md    # checklist, resultado dos testes e pendências (v4.0)
│   ├── TESTES_E_SEGURANCA_5.0.md    # testes e checklist da versão 5.0 (RH e comissões)
│   ├── TESTES_E_SEGURANCA_5.1.md    # testes finais e checklist da versão 5.1 (atual)
│   ├── RH_E_COMISSOES.md       # regras de comissão, folha e contracheque (v5.0)
│   └── RELATORIO_SEGURANCA_MEDFLOW_2026-09-30.pdf
│
├── docker-compose.yml          # orquestra mysql + backend + frontend
├── .env.example                 # modelo de variáveis de ambiente
├── SISTEMA_CLINICA.html         # sistema de uso diário (v5.1), abre com dois cliques
├── tests/
│   └── test_medflow_e2e.py      # testes automatizados do SISTEMA_CLINICA.html (Playwright)
├── CHANGELOG.md                 # histórico de versões
└── README.md                    # este arquivo
```

---

## Raiz do projeto (somente o necessário para rodar o sistema)

A pasta raiz contém apenas o necessário para o sistema (backend, frontend e
banco de dados) iniciar e funcionar: `backend/`, `frontend/`, `database/`,
`docs/`, `docker-compose.yml`, `.env`/`.env.example`, `.gitignore`, os
scripts `1-INICIAR-SISTEMA-COMPLETO.bat`, `INICIAR_SISTEMA.bat`,
`PARAR_SISTEMA.bat` e `setup_sem_docker.ps1`, este `README.md`, o `CHANGELOG.md`
e o `SISTEMA_CLINICA.html` (com suas imagens de logo e backups).

**Banco de dados do sistema:** existe um único banco de dados válido,
definido em `database/schema.sql` (com `database/seed_demo.sql` para dados de
exemplo) e usado exclusivamente pelo `backend/`.

### Sistema de uso diário na raiz: `SISTEMA_CLINICA.html` (versão 5.1)

Arquivo único (HTML e JavaScript autocontidos) que roda diretamente no navegador,
sem instalação e sem internet: basta dar dois cliques. Os dados ficam apenas
na memória do navegador, e tudo volta ao estado inicial quando a página é
recarregada. O arquivo usa um objeto `db` simulado em JavaScript, sem relação com
`database/schema.sql`, e fica na raiz da pasta junto com `logo-medflow.png` e
`logo-medflow-full.jpg`, imagens usadas na tela de acesso.

Cópias de segurança: `SISTEMA_CLINICA_BACKUP_20260930.html` e
`SISTEMA_CLINICA_BACKUP_20261001.html` (versão anterior à 4.0) e
`SISTEMA_CLINICA_BACKUP_20261002_v4.html` (versão 4.0) e
`SISTEMA_CLINICA_BACKUP_20261002_v5.0.html` (versão 5.0).

### Arquivos fora do sistema (em `extras-fora-do-sistema/`)

Os arquivos abaixo não fazem parte do backend, do frontend nem do banco de dados e não são
necessários para o sistema funcionar. Eles ficam isolados em
`extras-fora-do-sistema/` para não poluir a raiz do projeto, mas continuam
intactos, caso ainda sejam usados no dia a dia.

| Arquivo | O que é | Usa banco de dados? |
|---|---|---|
| `medflow-site-novo.html` | Site institucional de apresentação da clínica (marketing), com agendamento online via WhatsApp. | Não. É uma página estática; o agendamento gera uma mensagem de WhatsApp e não grava em nenhum banco. |
| `recibo-medflow.html` | Ferramenta avulsa para gerar recibo de atendimento (não é nota fiscal) para impressão ou envio por e-mail. | Não. O preenchimento é manual, sem persistência. |
| `banco01.docx` | Documento de projeto e proposta comercial (arquitetura, requisitos e modelagem do banco). É documentação de planejamento, não o banco em si. | Não. É o documento que descreve o banco. |
| `clinica 1.jpeg`, `clinica med Flow.jpeg` | Imagens avulsas da clínica, sem uso pelo código do sistema. | Não. |

### Limpeza de duplicados (concluída em 28/08/2026)

Ao longo do desenvolvimento, a pasta acumulou 6 cópias de backup
completas do projeto (cada uma com seus próprios `backend/`, `frontend/` e
`database/`), 5 arquivos `.zip` de backup e imagens de logo duplicadas.
Todos esses itens foram comparados arquivo a arquivo com a versão atual e
confirmados como desatualizados ou redundantes, sem nenhum conteúdo exclusivo.
Eles foram apagados permanentemente, o que liberou cerca de 5 MB de espaço em
disco. A pasta `_to_delete/` foi renomeada para `extras-fora-do-sistema/`,
pois agora contém apenas os arquivos avulsos ainda em uso (tabela acima),
e não mais itens a serem removidos.

---

## Usar em outro computador

- **SISTEMA_CLINICA.html:** copie o arquivo (e as duas imagens de logo) e abra-o
  com dois cliques. Não é necessário VS Code, extensão, internet nem instalação.
- **Versão completa (backend, frontend e banco de dados):** instale o Python 3.12
  (marcando a opção "Add python.exe to PATH"), o Node.js LTS e o MySQL Community Server;
  copie a pasta inteira (incluindo o `.env`) e execute o
  `1-INICIAR-SISTEMA-COMPLETO.bat`. O sistema abre em http://localhost:5173.
  Com o Docker Desktop instalado, use o `INICIAR_SISTEMA.bat`.
- **Extensões do VS Code:** são opcionais e servem apenas para editar o código (Python, ESLint,
  ES7+ React snippets, Tailwind CSS IntelliSense e um cliente MySQL). Para
  copiar as suas, use `code --list-extensions > extensoes.txt` e, no outro
  computador, `Get-Content extensoes.txt | ForEach-Object { code --install-extension $_ }`.

O passo a passo completo está em [`docs/Configuração do Sistema.pdf`](docs/Configuração%20do%20Sistema.pdf).

---

## Pré-requisitos

O sistema pode ser executado de duas formas: com Docker (recomendado, por ser mais
simples) ou sem Docker (executando cada parte manualmente).

### Opção recomendada: Docker

- [Docker Engine](https://docs.docker.com/engine/install/) 24 ou superior
- [Docker Compose](https://docs.docker.com/compose/install/) (plugin `docker compose`, já incluído nas instalações recentes do Docker Desktop e do Docker Engine)

Não é necessário instalar Python, Node.js ou MySQL na máquina, pois tudo roda
dentro dos containers.

### Alternativa: sem Docker

- Python 3.11 ou superior
- Node.js 20 ou superior (com npm)
- MySQL 8 (instância local ou remota já em execução)

---

## Como subir o ambiente com Docker (recomendado)

### 1. Clonar ou copiar o projeto e entrar na pasta

```bash
cd sistema-clinica
```

### 2. Criar o arquivo `.env` a partir do `.env.example`

```bash
cp .env.example .env
```

Abra o arquivo `.env` recém-criado e substitua todos os valores marcados
como `TROCAR_ESTE_VALOR` por valores reais e seguros:

| Variável | O que é |
|---|---|
| `SECRET_KEY` | Chave secreta do Flask (gere um valor aleatório longo) |
| `JWT_SECRET_KEY` | Chave secreta usada para assinar os tokens de login |
| `DB_USER` / `DB_PASSWORD` | Usuário e senha da aplicação no MySQL |
| `DB_ROOT_PASSWORD` | Senha do usuário `root` do MySQL (usada apenas na inicialização do container) |
| `FRONTEND_URL` | Origem (ou origens) permitida para CORS; em desenvolvimento local, `http://localhost:5173` |

Para gerar valores aleatórios seguros para `SECRET_KEY` e `JWT_SECRET_KEY`, use:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Nunca** faça commit do arquivo `.env` (ele já está no `.gitignore`) nem
reutilize os valores de exemplo em produção.

### 3. Subir os containers

```bash
docker compose up -d --build
docker compose exec backend flask --app wsgi definir-senha-admin
```

O primeiro comando:

- sobe um container MySQL 8, cria o banco definido em `DB_NAME` e aplica
  automaticamente o `database/schema.sql` na primeira inicialização (o que
  também cria as tabelas e o usuário administrador inicial, **sem senha válida**);
- sobe um Redis interno para o limite de tentativas de login;
- constrói e sobe o backend (API Flask), acessível só pela rede interna do Docker;
- constrói e sobe o frontend (React, servido via Nginx) na porta 5173, que
  também encaminha `/api` para o backend.

O segundo define a senha real do administrador (`admin@clinica.local`).

Para uma **demonstração** com pacientes fictícios e a senha de teste, use:

```bash
docker compose -f docker-compose.yml -f docker-compose.demo.yml up -d --build
```

O backend só inicia depois que o MySQL responde ao healthcheck; por isso, a
primeira inicialização pode levar alguns segundos a mais.

### 4. Acessar o sistema

- Frontend: [http://localhost:5173](http://localhost:5173)
- API (backend): pelo próprio frontend, em [http://localhost:5173/api/v1/health](http://localhost:5173/api/v1/health)
  (desde a versão 4.0.1, as portas 5000 e 3306 não ficam expostas no Docker)

### 5. Parar o ambiente

```bash
docker compose down
```

Para apagar também os dados do banco e recomeçar do zero:

```bash
docker compose down -v
```

---

## Como rodar sem Docker (manual)

### Banco de dados

1. Crie um banco MySQL (ex.: `clinica_odontologica`) e um usuário com
   permissão sobre ele.
2. Aplique o schema:
   ```bash
   mysql -u SEU_USUARIO -p clinica_odontologica < database/schema.sql
   ```
3. (Opcional) Carregue os dados de demonstração:
   ```bash
   mysql -u SEU_USUARIO -p clinica_odontologica < database/seed_demo.sql
   ```

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env         # edite os valores conforme a seção acima
export $(grep -v '^#' ../.env | xargs)   # carrega as variáveis no shell (Linux/Mac)
flask --app wsgi run --port 5000 --debug
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

O Vite normalmente inicia em `http://localhost:5173`. Confirme que o
frontend aponta para `http://localhost:5000` como URL da API (veja
`src/api/client.js` ou a variável de ambiente equivalente do Vite).

---

## Aviso importante sobre segurança e usuário administrador padrão

Para que o sistema funcione já na primeira inicialização, o `database/schema.sql`
cria um usuário administrador de exemplo:

- **E-mail:** `admin@clinica.local`
- **Senha:** placeholder de desenvolvimento (`TROCAR_NO_DEPLOY_HASH_PLACEHOLDER`), que não é uma senha válida. Sozinho, o `schema.sql` não permite nenhum login, de propósito.

Se você também executar o `database/seed_demo.sql` (que roda automaticamente
apenas com o `docker-compose.demo.yml` ou na instalação local sem Docker),
esse script substitui a senha do administrador por uma senha de teste válida,
apenas para que você possa explorar o sistema localmente:

- **E-mail:** `admin@clinica.local`
- **Senha:** `TesteSenha123!`

**Antes de usar o sistema com dados reais de pacientes, é obrigatório:**

1. Gerar um hash de senha real (bcrypt) para esse usuário e atualizá-lo no
   banco, ou criar um novo usuário administrador e desativar ou remover o de
   exemplo.
2. Trocar essa senha imediatamente após o primeiro acesso.
3. Revisar e trocar todos os segredos do `.env` (`SECRET_KEY`,
   `JWT_SECRET_KEY` e senhas de banco) por valores únicos e gerados
   aleatoriamente, sem reaproveitar os valores de exemplo ou placeholders.
4. Ler o documento de segurança antes de liberar o sistema para uso real
   (veja a seção abaixo).

Não use este projeto com dados reais de pacientes enquanto essas etapas não
forem concluídas.

---

## Principais módulos e telas

| Tela | Arquivo | Descrição |
|---|---|---|
| Login | `frontend/src/pages/Login.jsx` | Autenticação de usuários (e-mail e senha) e obtenção do token JWT |
| Dashboard | `frontend/src/pages/Dashboard.jsx` | Visão geral com indicadores da clínica (consultas do dia, resumo financeiro etc.) |
| Pacientes | `frontend/src/pages/Pacientes.jsx` | Cadastro, busca e edição de pacientes |
| Agenda | `frontend/src/pages/Agenda.jsx` | Agendamento e visualização de consultas |
| Prontuário | `frontend/src/pages/Prontuario.jsx` | Histórico clínico e odontograma do paciente (acesso restrito a administrador e dentista). No `SISTEMA_CLINICA.html` versão 4.0, o odontograma é anatômico 3D, com notação FDI |
| Financeiro | `frontend/src/pages/Financeiro.jsx` | Contas a pagar e a receber e controle de pagamentos |
| RH | somente no `SISTEMA_CLINICA.html` | Colaboradores, comissão dos dentistas, folha do mês e contracheques (versão 5.0) |

O acesso a cada módulo é controlado pelo perfil do usuário (administrador,
dentista, recepção e financeiro), definido no backend em
`backend/app/utils/auth_decorators.py` e nas rotas de cada módulo em
`backend/app/routes/`.

---

## Segurança

Este projeto passou por uma revisão de segurança do backend. O resultado
completo (problemas encontrados, correções já aplicadas e pendências)
está documentado em [`docs/SECURITY.md`](docs/SECURITY.md). A leitura desse
documento é obrigatória antes de qualquer uso além de estudo ou demonstração
local.

Os testes finais da versão 5.1 (02/10/2026) estão em
[`docs/TESTES_E_SEGURANCA_5.1.md`](docs/TESTES_E_SEGURANCA_5.1.md).
A auditoria da versão 4.0 (01/10/2026) está em
[`docs/TESTES_E_SEGURANCA_4.0.md`](docs/TESTES_E_SEGURANCA_4.0.md). As
pendências do backend apontadas nela (B1 a B14) foram corrigidas na versão
4.0.1 e conferidas nos testes finais de 02/10/2026. Continua pendente o MFA
(autenticação em dois fatores), além dos cuidados de implantação listados abaixo.

---

## Próximos passos para produção

Este repositório entrega um protótipo funcional. Antes de operar com dados
reais de pacientes em ambiente de produção, os itens abaixo, alinhados
à proposta original do projeto, ainda precisam ser concluídos:

- **Revisão de segurança humana:** revisão feita por uma pessoa qualificada
  (não automatizada), cobrindo autenticação, autorização por perfil, proteção
  de dados sensíveis (LGPD), gestão de segredos e infraestrutura, em
  complemento ao que já está descrito em `docs/SECURITY.md`.
- **Ambiente de hospedagem definitivo:** hoje, o `docker-compose.yml` é
  voltado para desenvolvimento e demonstração local. Para produção, é
  necessário definir e configurar um ambiente de hospedagem definitivo
  (servidor ou nuvem), com HTTPS, backups automáticos do banco de dados,
  monitoramento e política de atualização.
- **Treinamento da equipe da clínica:** capacitação da recepção, dos
  dentistas e da equipe financeira para o uso correto do sistema, incluindo boas
  práticas de proteção de dados de pacientes.
- **Manual de uso:** deve ser escrito somente depois que o sistema estiver
  finalizado e estável, para não descrever telas ou fluxos que ainda podem
  mudar.

Até que essas etapas sejam concluídas, o sistema deve ser tratado como uma
versão de avaliação e estudo, e não como um produto pronto para uso clínico real.
