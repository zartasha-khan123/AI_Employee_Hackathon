# Stop AI Employee services
# Usage: .\scripts\stop.ps1

Write-Host "Stopping AI Employee..." -ForegroundColor Yellow

# Find Python process running process_manager
$processes = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*process_manager*"
}

if ($processes) {
    foreach ($proc in $processes) {
        Write-Host "Stopping process (PID: $($proc.Id))..." -ForegroundColor Yellow
        Stop-Process -Id $proc.Id -Force
    }
    Write-Host "AI Employee stopped." -ForegroundColor Green
} else {
    Write-Host "AI Employee is not running." -ForegroundColor Red
}
