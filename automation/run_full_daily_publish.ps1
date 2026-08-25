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

$publishMode = Get-Content (Join-Path $root "automation\publish_mode.json") -Raw | ConvertFrom-Json
if ($publishMode.mode -ne "live") {
    throw "Daily publish flow is blocked because automation/publish_mode.json is '$($publishMode.mode)'."
}

$output = python automation\generate_random_daily_commander_bundle.py
if ($LASTEXITCODE -ne 0) {
    throw "Random Commander bundle generation failed with exit code $LASTEXITCODE."
}
$reportId = $null

foreach ($line in $output) {
    Write-Host $line
    if ($line -match '"report_id":\s*"([^"]+)"') {
        $reportId = $matches[1]
    }
}

if (-not $reportId) {
    throw "Could not determine report_id from the random daily commander generator."
}

& (Join-Path $root "automation\finalize_and_publish_bundle.ps1") -ReportId $reportId
