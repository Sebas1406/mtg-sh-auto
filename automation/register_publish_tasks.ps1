param(
    [string]$DailyTime = "08:00",
    [string]$TestAt = "",
    [string]$TestReportId = "",
    [switch]$SkipDaily
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$finalizeScript = Join-Path $root "automation\finalize_and_publish_bundle.ps1"

function Register-OrReplaceTask {
    param(
        [string]$TaskName,
        [Microsoft.Management.Infrastructure.CimInstance]$Trigger,
        [string]$Arguments
    )

    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $Arguments
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $Trigger -Force | Out-Null
    Write-Host "Registered scheduled task: $TaskName"
}

if (-not $SkipDaily) {
    $dailyTrigger = New-ScheduledTaskTrigger -Daily -At $DailyTime
    $dailyArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$finalizeScript`""
    Register-OrReplaceTask -TaskName "MTG SH Finalize And Publish Daily" -Trigger $dailyTrigger -Arguments $dailyArgs
}

if ($TestAt) {
    $testDateTime = [datetime]::Parse($TestAt)
    $testArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$finalizeScript`""
    if ($TestReportId) {
        $testArgs += " -ReportId `"$TestReportId`""
    }
    $testTrigger = New-ScheduledTaskTrigger -Once -At $testDateTime
    $taskName = "MTG SH Finalize And Publish Test " + $testDateTime.ToString("yyyy-MM-dd HHmm")
    Register-OrReplaceTask -TaskName $taskName -Trigger $testTrigger -Arguments $testArgs
}
