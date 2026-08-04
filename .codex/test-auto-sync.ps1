$ErrorActionPreference = "Stop"

$syncScript = Join-Path $PSScriptRoot "auto-sync.ps1"

& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $syncScript
if ($LASTEXITCODE -ne 0) {
    throw "auto-sync.ps1 exited with code $LASTEXITCODE"
}

Write-Output "auto-sync regression test passed"
