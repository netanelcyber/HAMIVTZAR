@echo off
REM Runs automatically at the end of Windows Setup, as NT AUTHORITY\SYSTEM,
REM before any user logs on. Windows Setup copies this file (and everything
REM alongside it) from sources\$OEM$\$$\Setup\Scripts\ on the installation
REM media to %WINDIR%\Setup\Scripts\ on the new install, then executes it.
REM See ..\..\..\..\..\README.md for how this gets built into the ISO.

set LOGDIR=%WINDIR%\Setup\Scripts\hardening-logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0hardening\Harden-WinServer2019.ps1" -Apply > "%LOGDIR%\harden-apply.log" 2>&1

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0hardening\Audit-WinServer2019.ps1" -ReportPath "%LOGDIR%\audit-after-install.txt" > "%LOGDIR%\audit-stdout.log" 2>&1
