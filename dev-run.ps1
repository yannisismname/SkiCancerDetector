# dev-run.ps1 - Start backend and frontend dev servers from repository root
# Run this from the repo root: PowerShell

$BackendDir = Join-Path $PSScriptRoot 'Backend'
$FrontendDir = Join-Path $PSScriptRoot 'frontend'

Write-Host "Starting Backend in $BackendDir"
Start-Process -NoNewWindow -FilePath "powershell.exe" -ArgumentList "-NoExit -Command cd '$BackendDir'; .\venv\Scripts\Activate.ps1; uvicorn main:app --host 0.0.0.0 --port 5000 --reload"

Start-Sleep -Seconds 2
Write-Host "Starting frontend static server in $FrontendDir"
Start-Process -NoNewWindow -FilePath "powershell.exe" -ArgumentList "-NoExit -Command cd '$FrontendDir'; python -m http.server 5500"

Write-Host "Servers started. Backend: http://localhost:5000, Frontend: http://localhost:5500"