# ==============================================================================
# BimaSakshi - One-Click Development Startup Script
# Great Indian AI Internship Challenge 2026
# ==============================================================================

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  STARTING BIMASAKSHI (AI HEALTH INSURANCE PRE-AUDIT PLATFORM)        " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"

# Check Python
$PythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    Write-Host "[ERROR] python.exe not found in PATH." -ForegroundColor Red
    exit 1
}

# Check Node / npm
$NpmCmd = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
if (-not $NpmCmd) {
    Write-Host "[ERROR] npm not found in PATH." -ForegroundColor Red
    exit 1
}

# Check backend .env
$EnvFile = Join-Path $BackendDir ".env"
if (-not (Test-Path $EnvFile)) {
    Write-Host "[WARNING] backend/.env file not found. Creating from .env.example..." -ForegroundColor Yellow
    Copy-Item (Join-Path $BackendDir ".env.example") $EnvFile
    Write-Host "[IMPORTANT] Please edit backend/.env and insert your GNANI_API_KEY and GEMINI_API_KEY." -ForegroundColor Yellow
}

Write-Host "`n[1/2] Starting FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Green
$BackendProcess = Start-Process -FilePath $PythonExe -ArgumentList "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $BackendDir -PassThru

Start-Sleep -Seconds 2

Write-Host "[2/2] Starting Vite React Frontend on http://localhost:5173..." -ForegroundColor Green
$FrontendProcess = Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory $FrontendDir -PassThru

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host "  BimaSakshi is now LIVE!                                             " -ForegroundColor Green
Write-Host "  Frontend Dashboard : http://localhost:5173                          " -ForegroundColor Yellow
Write-Host "  Backend API Docs   : http://127.0.0.1:8000/docs                     " -ForegroundColor Yellow
Write-Host "  Backend Health     : http://127.0.0.1:8000/health                   " -ForegroundColor Yellow
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Press Ctrl+C or close this terminal window to stop both processes.`n"

