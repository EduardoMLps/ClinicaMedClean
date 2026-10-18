@echo off
setlocal
cd /d "%~dp0"
title Sistema da Clinica - Instalacao e Inicializacao

echo ===================================================================
echo   SISTEMA DE GESTAO PARA CLINICA ODONTOLOGICA
echo   Instalacao e inicializacao automatica (sem Docker)
echo ===================================================================
echo.
echo  Esta janela vai:
echo    1. Verificar/instalar Python e Node.js
echo    2. Criar o banco de dados no MySQL que ja esta instalado
echo    3. Instalar as dependencias do backend e do frontend
echo    4. Subir o sistema e abrir o navegador
echo.
echo  Em algum momento ele vai PEDIR A SENHA DO ROOT DO MYSQL.
echo  Digite a senha e aperte Enter (a senha nao aparece na tela).
echo.
echo  Na primeira vez pode demorar alguns minutos. Nao feche esta janela.
echo ===================================================================
echo.
pause

if not exist "setup_sem_docker.ps1" (
    echo.
    echo ERRO: o arquivo setup_sem_docker.ps1 nao esta nesta pasta.
    echo Coloque este .bat na mesma pasta do setup_sem_docker.ps1.
    echo.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_sem_docker.ps1"

echo.
echo ===================================================================
echo  Se deu tudo certo, o sistema esta em: http://localhost:5173
echo  Login: admin@clinica.local   Senha: TesteSenha123!
echo ===================================================================
echo.
pause
