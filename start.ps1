# ========================================================
#   YuShu Robot Inventory - PowerShell One-Click Startup
#   Use this if .bat files have issues in your terminal
#   Right-click -> Run with PowerShell
# ========================================================

Set-Location $PSScriptRoot
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "============================================================"
Write-Host "  Starting YuShu Robot Inventory System" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host ""

# Check Python
try { python --version } catch {
    Write-Host "[ERROR] Python not found." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Node
$hasNode = $true
try { node --version } catch { $hasNode = $false }

if ($hasNode) {
    Write-Host "[1/3] Installing frontend dependencies..." -ForegroundColor Yellow
    Set-Location frontend
    if (-not (Test-Path "node_modules")) {
        npm install
    }
    Write-Host "[2/3] Building frontend..." -ForegroundColor Yellow
    npm run build
    Set-Location ..
}

Write-Host "[3/3] Starting backend..." -ForegroundColor Yellow
Set-Location backend
if (-not (Test-Path "venv")) {
    python -m venv venv
}
& "venv\Scripts\Activate.ps1" 2>$null
pip install -r requirements.txt -q
Write-Host ""
python run_external.py
Read-Host "Press Enter to exit"