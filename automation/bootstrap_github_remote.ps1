param(
    [string]$RepositoryUrl = "https://github.com/Sebas1406/mtg-sh-auto.git",
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

Require-Command git

$insideWorkTree = $false
$gitDir = Join-Path $root ".git"
if (Test-Path $gitDir) {
    $insideWorkTree = $true
}

if (-not $insideWorkTree) {
    git init -b $Branch
}

$hasOrigin = $false
$remoteUrl = ""
try {
    $remoteUrl = git remote get-url origin 2>$null
    if ($LASTEXITCODE -eq 0 -and $remoteUrl) {
        $hasOrigin = $true
    }
} catch {
    $hasOrigin = $false
}

if ($hasOrigin) {
    git remote set-url origin $RepositoryUrl
} else {
    git remote add origin $RepositoryUrl
}

Write-Host "Git remote configured:"
git remote -v
