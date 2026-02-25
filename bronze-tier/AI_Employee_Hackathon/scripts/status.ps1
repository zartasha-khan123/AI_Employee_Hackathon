# Check AI Employee status
# Usage: .\scripts\status.ps1

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "AI EMPLOYEE STATUS" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

# Check if process is running
$process = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*process_manager*"
}

if ($process) {
    Write-Host "Status: " -NoNewline
    Write-Host "RUNNING" -ForegroundColor Green
    Write-Host "PID: $($process.Id)"
    Write-Host "Started: $($process.StartTime)"
    Write-Host ""
} else {
    Write-Host "Status: " -NoNewline
    Write-Host "STOPPED" -ForegroundColor Red
    Write-Host ""
    Write-Host "To start: .\scripts\start.ps1" -ForegroundColor Yellow
    exit 0
}

# Check vault status
Write-Host "Vault Status:" -ForegroundColor Cyan
Write-Host "-------------"

$vaultPath = ".\vault"

if (Test-Path $vaultPath) {
    # Count files in each folder
    $needsAction = (Get-ChildItem "$vaultPath\Needs_Action" -Filter *.md -ErrorAction SilentlyContinue).Count
    $plans = (Get-ChildItem "$vaultPath\Plans" -Filter *.md -ErrorAction SilentlyContinue).Count
    $pendingApproval = (Get-ChildItem "$vaultPath\Pending_Approval" -Filter *.md -ErrorAction SilentlyContinue).Count
    $approved = (Get-ChildItem "$vaultPath\Approved" -Filter *.md -ErrorAction SilentlyContinue).Count
    $done = (Get-ChildItem "$vaultPath\Done" -Filter *.md -ErrorAction SilentlyContinue).Count
    $rejected = (Get-ChildItem "$vaultPath\Rejected" -Filter *.md -ErrorAction SilentlyContinue).Count

    Write-Host "  Needs Action:      $needsAction"
    Write-Host "  Plans:             $plans"

    if ($pendingApproval -gt 0) {
        Write-Host "  Pending Approval:  " -NoNewline
        Write-Host "$pendingApproval" -ForegroundColor Yellow
    } else {
        Write-Host "  Pending Approval:  $pendingApproval"
    }

    Write-Host "  Approved:          $approved"
    Write-Host "  Done:              $done"
    Write-Host "  Rejected:          $rejected"
    Write-Host ""

    # Show pending approvals if any
    if ($pendingApproval -gt 0) {
        Write-Host "Pending Approvals:" -ForegroundColor Yellow
        Write-Host "-----------------"
        Get-ChildItem "$vaultPath\Pending_Approval" -Filter *.md | ForEach-Object {
            Write-Host "  - $($_.Name)" -ForegroundColor Yellow
        }
        Write-Host ""
        Write-Host "To approve: python scripts/approve.py <filename>" -ForegroundColor Cyan
        Write-Host "To reject:  python scripts/reject.py <filename> <reason>" -ForegroundColor Cyan
        Write-Host ""
    }
} else {
    Write-Host "  Vault not found at: $vaultPath" -ForegroundColor Red
}

# Check configuration
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "-------------"

if (Test-Path ".\config\.env") {
    $envContent = Get-Content ".\config\.env" -Raw

    $devMode = if ($envContent -match "DEV_MODE=(\w+)") { $matches[1] } else { "unknown" }
    $dryRun = if ($envContent -match "DRY_RUN=(\w+)") { $matches[1] } else { "unknown" }

    Write-Host "  DEV_MODE:  " -NoNewline
    if ($devMode -eq "true") {
        Write-Host "$devMode" -ForegroundColor Yellow
    } else {
        Write-Host "$devMode" -ForegroundColor Green
    }

    Write-Host "  DRY_RUN:   " -NoNewline
    if ($dryRun -eq "true") {
        Write-Host "$dryRun" -ForegroundColor Yellow
    } else {
        Write-Host "$dryRun" -ForegroundColor Green
    }
} else {
    Write-Host "  .env file not found" -ForegroundColor Red
}

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan
