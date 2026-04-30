param(
    [string]$Branch = "main",
    [string]$Remote = "origin",
    [string]$ReportId = "",
    [string]$CommitMessage = ""
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
Require-Command python

if ($ReportId) {
    python automation/verify_publish_bundle.py $ReportId
} else {
    python automation/verify_publish_bundle.py
}

if (-not $CommitMessage) {
    if ($ReportId) {
        $CommitMessage = "chore: publish bundle $ReportId"
    } else {
        $CommitMessage = "chore: publish latest TikTok bundle"
    }
}

git add publish_queue legal-site/media legal-site/.nojekyll

$hasChanges = $true
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    $hasChanges = $false
}

if (-not $hasChanges) {
    Write-Host "No staged changes detected for publish bundle."
    exit 0
}

git commit -m $CommitMessage
git push $Remote $Branch

Write-Host "Publish bundle pushed successfully."
