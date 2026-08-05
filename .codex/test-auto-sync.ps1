$ErrorActionPreference = "Stop"

$silentLauncher = Join-Path $PSScriptRoot "auto-sync-silent.vbs"

& cscript.exe //B //NoLogo $silentLauncher
if ($LASTEXITCODE -ne 0) {
    throw "auto-sync-silent.vbs exited with code $LASTEXITCODE"
}

Write-Output "auto-sync regression test passed"
