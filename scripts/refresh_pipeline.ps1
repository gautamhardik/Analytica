# =============================================================================
# Analytica - Scheduled pipeline refresh (retrain ML + restart backend + tests)
#
# Usable from Windows Task Scheduler or manually:
#   powershell -ExecutionPolicy Bypass -File scripts\refresh_pipeline.ps1
#
# Skips retraining with:  powershell ... -File scripts\refresh_pipeline.ps1 -SkipRetrain
# =============================================================================
param([switch]$SkipRetrain)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$python = Join-Path $backend "venv\Scripts\python.exe"
$logFile = Join-Path $root "DOCS\logs\pipeline_refresh.log"

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $logFile) | Out-Null

function Write-Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

Write-Log "=== pipeline refresh started (SkipRetrain=$SkipRetrain) ==="

if (-not $SkipRetrain) {
    Write-Log "retraining ML models (forecast + segmentation)..."
    conda run -n base python "$root\ml\retrain.py" 2>&1 | ForEach-Object { Write-Log "  $_" }
    if ($LASTEXITCODE -ne 0) {
        Write-Log "retrain FAILED with exit code $LASTEXITCODE"
        exit 1
    }
    Write-Log "retrain OK"
}

# Restart the backend so it loads the refreshed forecast CSVs / artifacts.
$listeners = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue `
    | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($pid_ in $listeners) {
    Write-Log "stopping backend pid $pid_"
    Stop-Process -Id $pid_ -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2
Start-Process -FilePath $python -ArgumentList "-m", "uvicorn", "app.main:app", "--port", "8000" `
    -WorkingDirectory $backend -WindowStyle Hidden
Start-Sleep -Seconds 6
Write-Log "backend restarted"

# Run the backend test suite.
& $python -m pytest (Join-Path $backend "tests") -q 2>&1 | ForEach-Object { Write-Log "  $_" }
if ($LASTEXITCODE -ne 0) {
    Write-Log "backend tests FAILED"
    exit 1
}
Write-Log "backend tests OK"

Write-Log "=== pipeline refresh completed ==="
exit 0
