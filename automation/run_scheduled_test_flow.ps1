param(
    [Parameter(Mandatory = $true)]
    [string]$CommanderKey
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$output = python automation\generate_scheduled_test_bundle.py $CommanderKey
$reportId = $null

foreach ($line in $output) {
    if ($line -match '"report_id":\s*"([^"]+)"') {
        $reportId = $matches[1]
    }
}

if (-not $reportId) {
    throw "Could not determine generated report_id for commander key '$CommanderKey'."
}

& (Join-Path $root "automation\finalize_and_publish_bundle.ps1") -ReportId $reportId
