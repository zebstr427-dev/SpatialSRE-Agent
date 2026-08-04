$ErrorActionPreference = "Stop"

$repositoryPath = "C:\zyh\OnCallAgent\Python-super_biz_agent_py-release-2026-05-17\super_biz_agent_py-release-2026-05-17"
$logPath = Join-Path $repositoryPath ".git\auto-sync.log"
$lockPath = Join-Path $repositoryPath ".git\auto-sync.lock"
$env:GIT_TERMINAL_PROMPT = "0"

function Write-SyncLog {
    param([string]$Message)

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $logPath -Value "[$timestamp] $Message" -Encoding UTF8
}

$lockStream = $null

try {
    $lockStream = [System.IO.File]::Open(
        $lockPath,
        [System.IO.FileMode]::OpenOrCreate,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None
    )

    Set-Location -LiteralPath $repositoryPath

    $branch = (& git branch --show-current).Trim()
    if ($branch -ne "main") {
        Write-SyncLog "Skipped: current branch is '$branch', expected 'main'."
        exit 0
    }

    & git fetch origin main 2>&1 | ForEach-Object { Write-SyncLog $_ }
    if ($LASTEXITCODE -ne 0) {
        throw "git fetch failed with exit code $LASTEXITCODE"
    }

    $status = & git status --porcelain
    if ($status) {
        & git add -A
        if ($LASTEXITCODE -ne 0) {
            throw "git add failed with exit code $LASTEXITCODE"
        }

        & git diff --cached --quiet
        if ($LASTEXITCODE -ne 0) {
            $commitMessage = "chore(sync): auto-sync $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
            & git commit -m $commitMessage 2>&1 | ForEach-Object { Write-SyncLog $_ }
            if ($LASTEXITCODE -ne 0) {
                throw "git commit failed with exit code $LASTEXITCODE"
            }
        }
    }

    $counts = ((& git rev-list --left-right --count origin/main...HEAD).Trim() -split "\s+")
    $behind = [int]$counts[0]
    $ahead = [int]$counts[1]

    if ($behind -gt 0) {
        & git pull --rebase origin main 2>&1 | ForEach-Object { Write-SyncLog $_ }
        if ($LASTEXITCODE -ne 0) {
            throw "git pull --rebase failed with exit code $LASTEXITCODE"
        }
        $ahead = [int](((& git rev-list --left-right --count origin/main...HEAD).Trim() -split "\s+")[1])
    }

    if ($ahead -gt 0) {
        & git push origin main 2>&1 | ForEach-Object { Write-SyncLog $_ }
        if ($LASTEXITCODE -ne 0) {
            throw "git push failed with exit code $LASTEXITCODE"
        }
        Write-SyncLog "Synchronized main with origin/main."
    }
} catch [System.IO.IOException] {
    # Another scheduled run is already synchronizing this repository.
    exit 0
} catch {
    Write-SyncLog "ERROR: $($_.Exception.Message)"
    exit 1
} finally {
    if ($lockStream) {
        $lockStream.Dispose()
    }
}
