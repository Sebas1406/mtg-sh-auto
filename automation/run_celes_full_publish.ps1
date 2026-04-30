$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$resultJson = python automation\generate_celes_test_bundle.py | Select-Object -Last 5
$reportId = $null

foreach ($line in $resultJson) {
    if ($line -match '"report_id":\s*"([^"]+)"') {
        $reportId = $matches[1]
    }
}

if (-not $reportId) {
    throw "Could not determine generated report_id from Celes generation step."
}

& (Join-Path $root "automation\finalize_and_publish_bundle.ps1") -ReportId $reportId
