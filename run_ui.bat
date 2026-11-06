@echo off
setlocal EnableDelayedExpansion

REM =============================================================================
REM run_ui.bat - Carrega variaveis do .env e abre o pipeline_ui.py
REM =============================================================================

REM Diretorio onde este .bat esta localizado
set "BASE_DIR=%~dp0"
set "ENV_FILE=%BASE_DIR%.env"

REM Se nao existir .env, tenta .env.example
if not exist "%ENV_FILE%" (
    set "ENV_FILE=%BASE_DIR%.env.example"
    if not exist "%ENV_FILE%" (
        echo ERRO: nem .env nem .env.example encontrados em %BASE_DIR%
        pause
        exit /b 1
    )
    echo AVISO: .env nao encontrado, usando .env.example como base.
)

REM Carrega variaveis de ambiente do arquivo .env
REM Ignora linhas vazias e comentarios (#)
for /f "usebackq tokens=1,* delims==" %%A in ("%ENV_FILE%") do (
    echo %%A | findstr /b /c:"#" >nul 2>&1
    if errorlevel 1 (
        set "%%A=%%B"
    )
)

REM Ajusta codificacao do console para UTF-8
chcp 65001 >nul

REM Executa o Python do ambiente virtual diretamente (sem activate.bat, para evitar recursao)
set "VENV_PY=%BASE_DIR%.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo ERRO: python nao encontrado em %VENV_PY%
    pause
    exit /b 1
)

REM Entra na pasta scripts e executa a UI
cd /d "%BASE_DIR%\scripts"
"%VENV_PY%" pipeline_ui.py

endlocal
