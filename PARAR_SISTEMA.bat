@echo off
cd /d "%~dp0"
title Sistema da Clinica - Parando
echo Parando o sistema...
docker compose down
echo.
echo Sistema parado.
pause
