# Убирает автозапуск бота "Медовая лавка (тест)" и останавливает работающий экземпляр.
#
# Запуск:  powershell -ExecutionPolicy Bypass -File autostart-uninstall.ps1

$ErrorActionPreference = 'Continue'
$taskName = 'HoneyShopBot'

$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($task) {
    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host ('Zadacha ' + $taskName + ' udalena.')
} else {
    Write-Host ('Zadacha ' + $taskName + ' ne naydena.')
}

Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*bot.py*' -and $_.CommandLine -like '*honey-shop*' } |
    ForEach-Object { Write-Host ('Stop pid ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force }

Write-Host 'Gotovo.'
