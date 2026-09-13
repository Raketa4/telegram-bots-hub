# Автозапуск бота "Медовая лавка (тест)" через Планировщик задач Windows.
# Задача HoneyShopBot: старт при входе в систему, работа скрыто (pyw.exe),
# автоперезапуск при сбое.
#
# Запуск:  powershell -ExecutionPolicy Bypass -File autostart-install.ps1

$ErrorActionPreference = 'Stop'

$taskName = 'HoneyShopBot'
$botDir   = $PSScriptRoot
$botPy    = Join-Path $botDir 'bot.py'
$envFile  = Join-Path $botDir '.env'

if (-not (Test-Path $botPy))   { throw ('Nyet fayla: ' + $botPy) }
if (-not (Test-Path $envFile)) { throw 'Nyet .env - skopiruy .env.example v .env i vpishi token ot BotFather' }

$pyw = (Get-Command pyw.exe -ErrorAction SilentlyContinue).Source
if (-not $pyw) {
    foreach ($p in @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Launcher\pyw.exe'),
        (Join-Path $env:WINDIR 'pyw.exe')
    )) { if (Test-Path $p) { $pyw = $p; break } }
}
if (-not $pyw -or -not (Test-Path $pyw)) { throw 'pyw.exe ne nayden' }

$pyver = '-3.14'
& py $pyver -c "pass" 2>$null
if ($LASTEXITCODE -ne 0) { $pyver = '-3' }

Write-Host ('pyw     : ' + $pyw)
Write-Host ('pyver   : ' + $pyver)
Write-Host ('bot.py  : ' + $botPy)

$action    = New-ScheduledTaskAction -Execute $pyw -Argument ('{0} "{1}"' -f $pyver, $botPy) -WorkingDirectory $botDir
$trigger   = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartInterval (New-TimeSpan -Minutes 1) -RestartCount 999 -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Telegram bot honey-shop - long polling' -Force | Out-Null
} catch {
    Write-Warning ('Ne udalos sozdat zadachu: ' + $_.Exception.Message)
    Write-Host 'Zapusti PowerShell ot imeni administratora i povtori.'
    throw
}

Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*bot.py*' -and $_.CommandLine -like '*honey-shop*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep 2
Start-ScheduledTask -TaskName $taskName
Start-Sleep 5

Get-ScheduledTask -TaskName $taskName | Select-Object TaskName, State | Format-Table -AutoSize
$proc = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" | Where-Object { $_.CommandLine -like '*bot.py*' -and $_.CommandLine -like '*honey-shop*' }
if ($proc) { Write-Host ('Bot process pid: ' + $proc.ProcessId) } else { Write-Warning 'Process bot.py ne nayden - smotri bot.log' }

Write-Host ''
Write-Host 'Gotovo. Bot startuet pri vhode v sistemu i perezapuskaetsya pri sboe.'
Write-Host ('Logi:     ' + $botDir + '\bot.log')
Write-Host 'Status:   Get-ScheduledTask HoneyShopBot'
Write-Host ('Smotret:  Get-Content "' + $botDir + '\bot.log" -Tail 20 -Wait')
Write-Host ('Ubrat:    powershell -ExecutionPolicy Bypass -File "' + $botDir + '\autostart-uninstall.ps1"')
