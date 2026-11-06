# run_ui_premium.ps1 - Inicia backend FastAPI + frontend React (Vite)
$ErrorActionPreference = "Continue"

$BASE_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$VENV_PY = Join-Path $BASE_DIR ".venv\Scripts\python.exe"
$UI_DIR = Join-Path $BASE_DIR "ui"

Write-Host "[1/4] Verificando dependências Python..." -ForegroundColor Cyan
if (-not (Test-Path $VENV_PY)) {
    Write-Host "ERRO: Python do venv não encontrado em $VENV_PY" -ForegroundColor Red
    Read-Host "Pressione Enter para sair"
    exit 1
}

# Instala dependências Python se necessário
$check = & $VENV_PY -c "import fastapi, uvicorn" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Instalando fastapi uvicorn..." -ForegroundColor Cyan
    & $VENV_PY -m pip install fastapi uvicorn websockets pydantic 2>$null
}

# Instala dependências Node se necessário
Write-Host "[2/4] Verificando dependências Node..." -ForegroundColor Cyan
if (-not (Test-Path (Join-Path $UI_DIR "node_modules"))) {
    Write-Host "Instalando dependências do frontend (pode demorar)..." -ForegroundColor Cyan
    & npm install --prefix $UI_DIR 2>$null
}

# Inicia o backend FastAPI em background
Write-Host "[3/4] Iniciando backend API (http://127.0.0.1:8765)..." -ForegroundColor Cyan
$backendProc = Start-Process -FilePath $VENV_PY -ArgumentList "-m uvicorn server.api:app --host 127.0.0.1 --port 8765" -WorkingDirectory $BASE_DIR -PassThru -WindowStyle Hidden

# Aguarda o backend ficar online
Write-Host "Aguardando backend ficar online..." -ForegroundColor Cyan
$attempts = 0
while ($attempts -lt 30) {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8765/api/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) { break }
    } catch {}
    Start-Sleep -Seconds 1
    $attempts++
}
if ($attempts -ge 30) {
    Write-Host "ERRO: backend não respondeu a tempo." -ForegroundColor Red
    Read-Host "Pressione Enter para sair"
    exit 1
}
Write-Host "Backend online." -ForegroundColor Green

# Inicia o frontend React
Write-Host "[4/4] Iniciando frontend (http://localhost:5173)..." -ForegroundColor Cyan
$frontendProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory $UI_DIR -PassThru -WindowStyle Hidden

Write-Host ""
Write-Host "=============================================================================" -ForegroundColor Cyan
Write-Host "  VIDEOMAKER PREMIUM UI - ONLINE" -ForegroundColor Cyan
Write-Host "=============================================================================" -ForegroundColor Cyan
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "  Backend:  http://127.0.0.1:8765" -ForegroundColor White
Write-Host "  API Docs: http://127.0.0.1:8765/docs" -ForegroundColor White
Write-Host "=============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Pressione qualquer tecla para encerrar os servidores..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Encerra processos
try { $backendProc.Kill() } catch {}
try { $frontendProc.Kill() } catch {}
