# Start AI Employee services
# Usage: .\scripts\start.ps1

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "AI EMPLOYEE - SILVER TIER" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan

# Check if virtual environment exists
if (-not (Test-Path ".\.venv")) {
    Write-Host "Error: Virtual environment not found" -ForegroundColor Red
    Write-Host "Run: uv venv" -ForegroundColor Yellow
    exit 1
}

# Check if .env exists
if (-not (Test-Path ".\config\.env")) {
    Write-Host "Warning: .env file not found" -ForegroundColor Yellow
    Write-Host "Copy config/.env.example to config/.env and configure" -ForegroundColor Yellow
}

Write-Host "Starting AI Employee services..." -ForegroundColor Green
Write-Host ""

# Activate virtual environment and run process manager
& .\.venv\Scripts\Activate.ps1

# Run process manager
Write-Host "Press Ctrl+C to stop" -ForegroundColor Cyan
Write-Host ""

uv run python backend/orchestrator/process_manager.py

Write-Host ""
Write-Host "AI Employee stopped." -ForegroundColor Yellow
