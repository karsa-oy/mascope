@echo off
set mypath=%~dp0
set project_path=%~dpnx1

if not exist %project_path% (
  echo Error: mascope project not found in %project_path%
  exit /b 1
)


:start
echo ** Check for latest commits...
cd %project_path%
git log -n 1 >%mypath%\last_commit_1.txt
git pull > nul
git log -n 1 >%mypath%\last_commit_2.txt
fc %mypath%\last_commit_1.txt %mypath%\last_commit_2.txt>nul && (echo %date% %time% -- No changes & goto :again)
call %mypath%\_deploy.cmd %project_path%
goto :again

:again
timeout 20
goto :start
