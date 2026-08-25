param(
    [string]$ReportId = "",
    [string]$Branch = "main",
    [string]$Remote = "origin",
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

Require-Command python
Require-Command git

$pushArgs = @{
    Branch = $Branch
    Remote = $Remote
}

if ($ReportId) {
    python automation/stage_tiktok_media.py $ReportId
    if ($LASTEXITCODE -ne 0) {
        throw "Media staging failed for $ReportId with exit code $LASTEXITCODE."
    }
    $pushArgs.ReportId = $ReportId
} else {
    throw "ReportId is required so finalization cannot select an unintended queue item."
}

if ($CommitMessage) {
    $pushArgs.CommitMessage = $CommitMessage
}

& (Join-Path $root "automation\push_publish_bundle.ps1") @pushArgs

Write-Host "Local bundle finalized and pushed. GitHub Actions will handle Pages and TikTok."
