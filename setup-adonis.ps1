$batPath = Join-Path $PSScriptRoot "start-adonis-server.bat"
$cmd = "cmd /c start `"Adonis Server`" `"$batPath`""

New-Item -Path "HKCU:\Software\Classes\adonis-refresh" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\adonis-refresh" -Name "(default)" -Value "Adonis Refresh Server"
New-ItemProperty -Path "HKCU:\Software\Classes\adonis-refresh" -Name "URL Protocol" -Value "" -Force | Out-Null
New-Item -Path "HKCU:\Software\Classes\adonis-refresh\shell\open\command" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\adonis-refresh\shell\open\command" -Name "(default)" -Value $cmd

Write-Host "Done! The Block Summary Refresh button will now auto-start the server." -ForegroundColor Green
Write-Host "You only need to run this setup once." -ForegroundColor Gray
Read-Host "Press Enter to exit"
