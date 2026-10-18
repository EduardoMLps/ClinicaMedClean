@echo off
cd /d "%~dp0"
title Sistema da Clinica - Inicializando

where docker >nul 2>nul
if errorlevel 1 (
    echo.
    echo ===================================================================
    echo  O Docker Desktop nao foi encontrado neste computador.
    echo.
    echo  Baixe e instale em: https://www.docker.com/products/docker-desktop/
    echo  Depois de instalar, abra o Docker Desktop uma vez, espere ele
    echo  terminar de iniciar (icone da baleia fica paradinho na bandeja
    echo  do Windows, perto do relogio), e clique de novo neste arquivo.
    echo ===================================================================
    echo.
    pause
    exit /b 1
)

if not exist .env (
    copy .env.example .env >nul
    echo Arquivo .env criado a partir do .env.example.
)

echo.
echo Iniciando o sistema da clinica...
echo Na primeira vez isso pode demorar alguns minutos (baixando e
echo instalando tudo). Nas proximas vezes e bem mais rapido.
echo.
echo NAO FECHE ESTA JANELA enquanto estiver usando o sistema.
echo Quando aparecer bastante texto e "parar de rolar", abra o navegador em:
echo.
echo      http://localhost:5173
echo.
echo Login: admin@clinica.local   /   Senha: TesteSenha123!
echo.

docker compose up --build

echo.
echo O sistema foi encerrado.
pause
