$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = (Get-Command python).Source
$pipelineScript = Join-Path $root "automation\run_daily_pipeline.py"
$publishScript = Join-Path $root "automation\show_publish_window.py"

$tasks = @(
    @{
        Name = "MTG Commander Daily Pipeline"
        Time = "08:05"
        Frequency = "Daily"
        Command = "`"$python`" `"$pipelineScript`""
    }
    @{
        Name = "MTG Commander Publish Monday"
        Time = "13:00"
        Frequency = "Weekly"
        DayOfWeek = "Monday"
        Command = "`"$python`" `"$publishScript`" monday"
    }
    @{
        Name = "MTG Commander Publish Tuesday"
        Time = "12:00"
        Frequency = "Weekly"
        DayOfWeek = "Tuesday"
        Command = "`"$python`" `"$publishScript`" tuesday"
    }
    @{
        Name = "MTG Commander Publish Wednesday"
        Time = "17:00"
        Frequency = "Weekly"
        DayOfWeek = "Wednesday"
        Command = "`"$python`" `"$publishScript`" wednesday"
    }
    @{
        Name = "MTG Commander Publish Thursday"
        Time = "17:00"
        Frequency = "Weekly"
        DayOfWeek = "Thursday"
        Command = "`"$python`" `"$publishScript`" thursday"
    }
    @{
        Name = "MTG Commander Publish Friday"
        Time = "18:00"
        Frequency = "Weekly"
        DayOfWeek = "Friday"
        Command = "`"$python`" `"$publishScript`" friday"
    }
    @{
        Name = "MTG Commander Publish Saturday"
        Time = "17:00"
        Frequency = "Weekly"
        DayOfWeek = "Saturday"
        Command = "`"$python`" `"$publishScript`" saturday"
    }
    @{
        Name = "MTG Commander Publish Sunday"
        Time = "09:00"
        Frequency = "Weekly"
        DayOfWeek = "Sunday"
        Command = "`"$python`" `"$publishScript`" sunday"
    }
)

foreach ($task in $tasks) {
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -WindowStyle Hidden -Command $($task.Command)"
    if ($task.Frequency -eq "Daily") {
        $trigger = New-ScheduledTaskTrigger -Daily -At $task.Time
    }
    else {
        $trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek $task.DayOfWeek -At $task.Time
    }

    Register-ScheduledTask -TaskName $task.Name -Action $action -Trigger $trigger -Force | Out-Null
    Write-Host "Registered scheduled task: $($task.Name)"
}
