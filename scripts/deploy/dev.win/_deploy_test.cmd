@echo off
set mypath=%~dp0
set project_path=%~dpnx1

echo ** Stopping current version...
cd %project_path%
call %mypath%\_kill.cmd

echo Set MASCOPE environment...
copy /y %mypath%\.env %project_path%\.env

echo Override with MASCOPE test environment...
echo. >> %project_path%\.env
type %mypath%\.test_env >> %project_path%\.env

FOR /F "eol=# tokens=*" %%i IN (%project_path%\.env) DO SET %%i

echo ** Installing latest version...
cd %project_path%
call %mypath%\_install.cmd

echo ** Starting latest version...
cd %project_path%
call %mypath%\_start.cmd
