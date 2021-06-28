@echo off

echo Mascope automation host setup
echo to be run with elevated privileges

rem Map \\vboxsrv\/vagrant as z:
if not exist z:\ (
 timeout 5
 net use z: \\192.168.1.42 >nul 2>&1
 if not exist z:\ exit /b 2
)

echo Disable UAC
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v EnableLUA /t REG_DWORD /d 0 /f  || goto :error

echo Disable automatic update
reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update" /v AUOptions /t REG_DWORD /d 1 /f || goto :error

echo Disable auto reboot
reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU" /v NoAutoRebootWithLoggedOnUsers /t REG_DWORD /d 1 /f || goto :error

echo Disable hibernation, standby and disk stop
powercfg /x -hibernate-timeout-ac 0 || goto :error
powercfg /x -hibernate-timeout-dc 0 || goto :error
powercfg /x -disk-timeout-ac 0 || goto :error
powercfg /x -disk-timeout-dc 0 || goto :error
::powercfg /x -monitor-timeout-ac 0 || goto :error
::powercfg /x -monitor-timeout-dc 0 || goto :error
Powercfg /x -standby-timeout-ac 0 || goto :error
powercfg /x -standby-timeout-dc 0 || goto :error

exit /b 0


:error
set err=%ERRORLEVEL%
echo ========================
echo Failed with error %err%
echo ========================
exit /b %err%