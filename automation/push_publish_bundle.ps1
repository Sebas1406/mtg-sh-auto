param(
    [string]$Branch = "main",
    [string]$Remote = "origin",
    [string]$ReportId = "",
    [string]$CommitMessage = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$gitCmdPath = "C:\Program Files\Git\cmd"
if ((Test-Path $gitCmdPath) -and (($env:Path -split ';') -notcontains $gitCmdPath)) {
    $env:Path = "$env:Path;$gitCmdPath"
}

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

Require-Command git
Require-Command python

function Invoke-Git {
    param([string[]]$GitArguments)
    & git @GitArguments
    if ($LASTEXITCODE -ne 0) {
        throw "git $($GitArguments -join ' ') failed with exit code $LASTEXITCODE."
    }
}

if ($ReportId) {
    python automation/verify_publish_bundle.py $ReportId
    if ($LASTEXITCODE -ne 0) {
        throw "Publish-bundle verification failed for $ReportId with exit code $LASTEXITCODE."
    }
} else {
    throw "ReportId is required so verification cannot select an unintended queue item."
}

if (-not $CommitMessage) {
    if ($ReportId) {
        $CommitMessage = "chore: publish bundle $ReportId"
    } else {
        $CommitMessage = "chore: publish latest TikTok bundle"
    }
}

if ($ReportId) {
    $artifactPaths = @(
        "publish_queue/$ReportId.json",
        "legal-site/media/$ReportId",
        "commander_selection_runs/$ReportId.json",
        "deck_manifests/$ReportId.json",
        "deck_validation/$ReportId.json",
        "report_data/$ReportId.json",
        "reports/$ReportId.md",
        "moxfield_decklists_100/$ReportId.txt"
    )
    foreach ($artifactPath in $artifactPaths) {
        if (-not (Test-Path -LiteralPath (Join-Path $root $artifactPath))) {
            throw "Required publish artifact is missing: $artifactPath"
        }
    }
    $gitAddArguments = @("add", "--") + $artifactPaths
    Invoke-Git -GitArguments $gitAddArguments
} else {
    throw "ReportId is required so the publisher cannot stage unrelated or historical artifacts."
}

$hasChanges = $true
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    $hasChanges = $false
}

if (-not $hasChanges) {
    Write-Host "No staged changes detected for publish bundle."
    exit 0
}

Invoke-Git -GitArguments @("commit", "-m", $CommitMessage)
Invoke-Git -GitArguments @("push", $Remote, $Branch)

Write-Host "Publish bundle pushed successfully."
