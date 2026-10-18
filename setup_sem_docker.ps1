#requires -version 5
<#
    Configura e inicia o Sistema de Gestao para Clinica Odontologica
    SEM Docker -- roda o backend (Python/Flask) e o frontend (Node/Vite)
    direto na maquina, usando um MySQL Server ja instalado localmente.

    Seguro rodar mais de uma vez (idempotente): pula passos ja feitos.
#>

$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
Set-Location $raiz

function Titulo($texto) {
    Write-Host ""
    Write-Host "=== $texto ===" -ForegroundColor Cyan
}

function Atualizar-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + `
                [System.Environment]::GetEnvironmentVariable("Path", "User")
}

function Comando-Existe($nome) {
    return [bool](Get-Command $nome -ErrorAction SilentlyContinue)
}

# ---------------------------------------------------------------------
# 1. Python
# ---------------------------------------------------------------------
Titulo "Verificando Python"

# Descobre o python de varias formas: PATH, launcher "py", e as pastas
# padrao de instalacao (o instalador do python.org nem sempre atualiza o PATH
# de uma janela de terminal que ja estava aberta).
function Descobrir-Python {
    if (Comando-Existe "python") {
        # No Windows existe um "python.exe" falso em WindowsApps que so abre a
        # Microsoft Store. Ele responde ao Get-Command mas nao executa nada.
        $caminho = (Get-Command python).Source
        if ($caminho -notlike "*WindowsApps*") { return $true }
    }
    # 1) launcher oficial "py"
    if (Comando-Existe "py") {
        $achado = & py -c "import sys,os;print(os.path.dirname(sys.executable))" 2>$null
        if ($LASTEXITCODE -eq 0 -and $achado) {
            $env:Path = "$achado;$env:Path"
            if (Comando-Existe "python") { return $true }
        }
    }
    # 2) pastas padrao de instalacao
    $bases = @(
        "$env:LOCALAPPDATA\Programs\Python",
        "$env:ProgramFiles\Python*",
        "C:\Python*"
    )
    foreach ($base in $bases) {
        $exes = Get-ChildItem -Path $base -Filter "python.exe" -Recurse -Depth 2 -ErrorAction SilentlyContinue |
                Sort-Object FullName -Descending
        if ($exes) {
            $dir = Split-Path $exes[0].FullName -Parent
            $env:Path = "$dir;$dir\Scripts;$env:Path"
            if (Comando-Existe "python") { return $true }
        }
    }
    return $false
}

if (-not (Descobrir-Python)) {
    Atualizar-Path
}
if (-not (Descobrir-Python)) {
    if (Comando-Existe "winget") {
        Write-Host "Python nao encontrado. Instalando via winget (Python 3.12)..."
        winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
        Start-Sleep -Seconds 3
        Atualizar-Path
    }
    if (-not (Descobrir-Python)) {
        Write-Host ""
        Write-Host "ERRO: Nao consegui instalar/encontrar o Python automaticamente." -ForegroundColor Red
        Write-Host "Instale manualmente em https://www.python.org/downloads/ (marque 'Add python.exe to PATH')"
        Write-Host "e rode este script de novo." -ForegroundColor Red
        Read-Host "Pressione Enter para sair"
        exit 1
    }
}
Write-Host "OK: $(python --version)" -ForegroundColor Green

# ---------------------------------------------------------------------
# 2. Node.js
# ---------------------------------------------------------------------
Titulo "Verificando Node.js"
if (-not (Comando-Existe "node")) {
    if (Comando-Existe "winget") {
        Write-Host "Node.js nao encontrado. Instalando via winget (LTS)..."
        winget install -e --id OpenJS.NodeJS.LTS --silent --accept-package-agreements --accept-source-agreements
        Start-Sleep -Seconds 3
        Atualizar-Path
    }
    if (-not (Comando-Existe "node")) {
        Write-Host ""
        Write-Host "ERRO: Nao consegui instalar/encontrar o Node.js automaticamente." -ForegroundColor Red
        Write-Host "Instale manualmente em https://nodejs.org/ (versao LTS) e rode este script de novo." -ForegroundColor Red
        Read-Host "Pressione Enter para sair"
        exit 1
    }
}
Write-Host "OK: node $(node --version) / npm $(npm --version)" -ForegroundColor Green

# ---------------------------------------------------------------------
# 3. MySQL -- precisa ja estar instalado (nao tentamos instalar sozinho,
#    pois a instalacao do MySQL Server pede configuracao interativa).
# ---------------------------------------------------------------------
Titulo "Verificando MySQL"

if (-not (Comando-Existe "mysql")) {
    $candidatos = Get-ChildItem "C:\Program Files\MySQL" -Directory -ErrorAction SilentlyContinue |
        ForEach-Object { Join-Path $_.FullName "bin\mysql.exe" } |
        Where-Object { Test-Path $_ }
    if ($candidatos) {
        $binDir = Split-Path $candidatos[0] -Parent
        $env:Path = "$binDir;$env:Path"
        Write-Host "Encontrado mysql.exe em $binDir (adicionado ao PATH desta sessao)."
    }
}

if (-not (Comando-Existe "mysql")) {
    Write-Host ""
    Write-Host "ERRO: Nao encontrei um MySQL Server instalado nesta maquina." -ForegroundColor Red
    Write-Host "Instale o MySQL Community Server (com o MySQL Installer, marcando"
    Write-Host "'MySQL Server') em: https://dev.mysql.com/downloads/installer/"
    Write-Host "Durante a instalacao, defina uma senha para o usuario 'root' e anote ela."
    Write-Host "Depois rode este script de novo." -ForegroundColor Red
    Read-Host "Pressione Enter para sair"
    exit 1
}
Write-Host "OK: mysql client encontrado." -ForegroundColor Green

# Garante que o servico do MySQL esta rodando (se existir como servico Windows).
$servicoMysql = Get-Service -Name "MySQL*" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($servicoMysql -and $servicoMysql.Status -ne "Running") {
    Write-Host "Iniciando o servico do MySQL ($($servicoMysql.Name))..."
    Start-Service $servicoMysql.Name
    Start-Sleep -Seconds 3
}

# ---------------------------------------------------------------------
# 4. Credenciais do MySQL root (so pergunta na tela, nunca fica salvo)
# ---------------------------------------------------------------------
Titulo "Conectando ao MySQL como root"
Write-Host "Digite a senha do usuario 'root' do MySQL (a mesma que voce definiu"
Write-Host "quando instalou o MySQL). Se root nao tiver senha, so aperte Enter."
$rootSecure = Read-Host "Senha do root do MySQL" -AsSecureString
$rootPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($rootSecure)
)

function Rodar-MySQL-Root {
    param(
        [Parameter(Mandatory = $true)][string]$Sql,
        [switch]$EhArquivo
    )
    $mysqlArgs = @("-uroot", "--default-character-set=utf8mb4")
    if ($rootPlain) { $mysqlArgs += "-p$rootPlain" }

    if ($EhArquivo) {
        Get-Content $Sql -Raw | & mysql @mysqlArgs
    } else {
        $mysqlArgs += @("-e", $Sql)
        & mysql @mysqlArgs
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao rodar comando no MySQL (confira a senha do root)."
    }
}

try {
    Rodar-MySQL-Root -Sql "SELECT 1;"
} catch {
    Write-Host ""
    Write-Host "ERRO: Nao consegui conectar no MySQL com essa senha de root." -ForegroundColor Red
    Read-Host "Pressione Enter para sair"
    exit 1
}
Write-Host "OK: conectado no MySQL." -ForegroundColor Green

# ---------------------------------------------------------------------
# 5. Cria banco + usuario da aplicacao (idempotente) + carrega schema/seed
# ---------------------------------------------------------------------
Titulo "Criando banco de dados e usuario da aplicacao"

$appDbPassword = -join ((48..57) + (97..122) + (65..90) | Get-Random -Count 20 | ForEach-Object {[char]$_})

Rodar-MySQL-Root -Sql @"
CREATE DATABASE IF NOT EXISTS clinica_odontologica CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS 'clinica_app'@'localhost' IDENTIFIED BY '$appDbPassword';
ALTER USER 'clinica_app'@'localhost' IDENTIFIED BY '$appDbPassword';
GRANT ALL PRIVILEGES ON clinica_odontologica.* TO 'clinica_app'@'localhost';
FLUSH PRIVILEGES;
"@

$mysqlArgsCheck = @("-uroot", "--default-character-set=utf8mb4", "-N", "-e",
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='clinica_odontologica' AND table_name='usuarios';")
if ($rootPlain) { $mysqlArgsCheck += "-p$rootPlain" }
$jaExiste = (& mysql @mysqlArgsCheck 2>$null | Select-Object -First 1).Trim()

if ($jaExiste -eq "1") {
    Write-Host "Banco de dados ja estava configurado (tabela 'usuarios' encontrada) -- pulando schema.sql e seed_demo.sql."
    Write-Host "Se quiser recarregar os dados de teste do zero, apague o banco 'clinica_odontologica' no MySQL Workbench e rode este script de novo."
} else {
    Write-Host "Carregando schema.sql..."
    Rodar-MySQL-Root -EhArquivo -Sql (Join-Path $raiz "database\schema.sql")

    Write-Host "Carregando seed_demo.sql (dados de teste + senha do admin)..."
    Rodar-MySQL-Root -EhArquivo -Sql (Join-Path $raiz "database\seed_demo.sql")
}

Write-Host "OK: banco de dados pronto." -ForegroundColor Green

# ---------------------------------------------------------------------
# 6. Arquivo .env do backend
# ---------------------------------------------------------------------
Titulo "Gerando backend\.env"

function Gerar-Chave {
    -join ((48..57) + (97..122) + (65..90) | Get-Random -Count 48 | ForEach-Object {[char]$_})
}

$secretKey = Gerar-Chave
$jwtKey = Gerar-Chave

$envContent = @"
FLASK_ENV=development
FLASK_DEBUG=false
SECRET_KEY=$secretKey
JWT_SECRET_KEY=$jwtKey
JWT_ACCESS_TOKEN_EXPIRES_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRES_DAYS=7
DB_HOST=localhost
DB_PORT=3306
DB_NAME=clinica_odontologica
DB_USER=clinica_app
DB_PASSWORD=$appDbPassword
FRONTEND_URL=http://localhost:5173
RATELIMIT_STORAGE_URI=memory://
"@
Set-Content -Path (Join-Path $raiz "backend\.env") -Value $envContent -Encoding UTF8
Write-Host "OK: backend\.env criado." -ForegroundColor Green

# ---------------------------------------------------------------------
# 7. Backend: venv + dependencias
# ---------------------------------------------------------------------
Titulo "Preparando o backend (Python)"
$backendPath = Join-Path $raiz "backend"
$venvPython = Join-Path $backendPath ".venv\Scripts\python.exe"

Push-Location $backendPath
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& $venvPython -m pip install --upgrade pip --quiet
& $venvPython -m pip install -r requirements.txt --quiet
Pop-Location
Write-Host "OK: dependencias do backend instaladas." -ForegroundColor Green

# ---------------------------------------------------------------------
# 8. Frontend: dependencias npm
# ---------------------------------------------------------------------
Titulo "Preparando o frontend (Node)"
$frontendPath = Join-Path $raiz "frontend"
Push-Location $frontendPath
if (-not (Test-Path "node_modules")) {
    npm install
}
Pop-Location
Write-Host "OK: dependencias do frontend instaladas." -ForegroundColor Green

# ---------------------------------------------------------------------
# 9. Sobe backend e frontend, cada um em sua propria janela.
#    Usa o python.exe do venv diretamente (via "-m flask"), sem precisar
#    ativar o venv -- assim nao depende da politica de execucao de script
#    do PowerShell na janela nova.
# ---------------------------------------------------------------------
Titulo "Iniciando o sistema"

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$backendPath'; & '$venvPython' -m flask --app wsgi run --port 5000"
)

Start-Sleep -Seconds 3

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$frontendPath'; npm run dev"
)

Write-Host ""
Write-Host "Abriram duas novas janelas do PowerShell (backend e frontend)." -ForegroundColor Yellow
Write-Host "NAO FECHE ELAS enquanto estiver usando o sistema." -ForegroundColor Yellow
Write-Host ""
Write-Host "Esperando o frontend subir..."
Start-Sleep -Seconds 8

Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Green
Write-Host " Pronto! Se o navegador nao abriu sozinho, acesse:"
Write-Host "     http://localhost:5173"
Write-Host ""
Write-Host " Login:  admin@clinica.local"
Write-Host " Senha:  TesteSenha123!"
Write-Host "=========================================================" -ForegroundColor Green
Read-Host "Pressione Enter para fechar esta janela (as outras duas continuam abertas)"



Resumo do ponto de parada (Kali + adaptador COMFAST RTL8812AU):



DESCOBRIR SENHA 

Aqui estão os três comandos, cada um separado pra você copiar um de cada vez na Kali:

1️⃣ Criar o rockyou filtrado (senhas ≥8 caracteres, ideal pro WPA):

awk 'length >= 8' /usr/share/wordlists/rockyou.txt > /usr/share/wordlists/rockyou-wpa.txt && echo ">>> criada" && ls -lh /usr/share/wordlists/rockyou-wpa.txt && wc -l /usr/share/wordlists/rockyou-wpa.txt


2️⃣ Fixar a rede (pro wlan0 não cair quando o wifite matar o NetworkManager):

sudo ip addr add 10.0.2.15/24 dev eth0 2>/dev/null; sudo ip route replace default via 10.0.2.2; echo ">>> rede fixada"



3️⃣ Rodar o wifite com a wordlist filtrada:


sudo wifite --dict /usr/share/wordlists/rockyou-wpa.txt
