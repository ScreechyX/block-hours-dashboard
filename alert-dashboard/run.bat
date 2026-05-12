@echo off
echo.
echo  Alert Intelligence Dashboard
echo  ============================
echo.
echo  This will open a file picker to select your PST file.
echo  Outlook must be installed (it does not need to be open).
echo.
powershell.exe -ExecutionPolicy Bypass -File "%~dp0extract.ps1"
