@echo off
setlocal

set "BASE_DIR=%~dp0"
set "VENV_PY=%BASE_DIR%.venv\Scripts\python.exe"
set "UI_DIR=%BASE_DIR%ui"

echo Iniciando backend...
start "" /b "%VENV_PY%" -m uvicorn server.api:app --host 127.0.0.1 --port 8765

echo Aguardando backend...
:wait
"%VENV_PY%" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/health', timeout=2)" >nul 2>&1
if errorlevel 1 goto wait

echo Iniciando frontend...
cd /d "%UI_DIR%"
start "" /b cmd /c npm run dev

echo ONLINE: http://localhost:5173
pause
