param(
    [string[]]$CommanderRotation = @("kaalia", "chulane", "giada", "yarok", "omnath")
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

if (-not $CommanderRotation -or $CommanderRotation.Count -eq 0) {
    throw "Commander rotation cannot be empty."
}

$dayIndex = (Get-Date).DayOfYear - 1
$selectedKey = $CommanderRotation[$dayIndex % $CommanderRotation.Count]

Write-Host "Selected commander key for today's full daily flow: $selectedKey"

& (Join-Path $root "automation\run_scheduled_test_flow.ps1") -CommanderKey $selectedKey
