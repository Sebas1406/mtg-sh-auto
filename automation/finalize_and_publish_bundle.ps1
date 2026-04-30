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

if ($ReportId) {
    python automation/stage_tiktok_media.py $ReportId
    powershell -ExecutionPolicy Bypass -File automation/push_publish_bundle.ps1 -ReportId $ReportId -Branch $Branch -Remote $Remote -CommitMessage $CommitMessage
} else {
    python automation/stage_tiktok_media.py
    powershell -ExecutionPolicy Bypass -File automation/push_publish_bundle.ps1 -Branch $Branch -Remote $Remote -CommitMessage $CommitMessage
}

Write-Host "Local bundle finalized and pushed. GitHub Actions will handle Pages and TikTok."
