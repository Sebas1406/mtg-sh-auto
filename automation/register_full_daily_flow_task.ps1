param(
    [string]$DailyTime = "08:00"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$script = Join-Path $root "automation\run_full_daily_publish.ps1"
$taskName = "MTG SH Full Generate And Publish Daily"
$legacyTaskName = "MTG SH Finalize And Publish Daily"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`""
$trigger = New-ScheduledTaskTrigger -Daily -At $DailyTime

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Force | Out-Null
Write-Host "Registered scheduled task: $taskName"

try {
    Disable-ScheduledTask -TaskName $legacyTaskName | Out-Null
    Write-Host "Disabled legacy task: $legacyTaskName"
} catch {
    Write-Host "Legacy task not found or could not be disabled: $legacyTaskName"
}
