# ========================================================
#   YuShu Robot Inventory - Dev Mode (PowerShell)
#   Right-click -> Run with PowerShell
# ========================================================

Set-Location $PSScriptRoot
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "============================================================"
Write-Host "  Dev Mode - Backend + Frontend" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host ""

# Start backend in a new window
Start-Process -FilePath "python" -ArgumentList "run_external.py" `
    -WorkingDirectory "$PSScriptRoot\backend" `
    -WindowStyle Normal

Start-Sleep -Seconds 3

# Start frontend dev server in a new window
Start-Process -FilePath "npm" -ArgumentList "run", "dev" `
    -WorkingDirectory "$PSScriptRoot\frontend" `
    -WindowStyle Normal

Write-Host "Both services started in new windows." -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "  API Doc:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor White
Write-Host ""
Read-Host "Press Enter to exit"