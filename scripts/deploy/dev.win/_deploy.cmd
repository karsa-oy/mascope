@echo off
set mypath=%~dp0
set project_path=%~dpnx1

echo ** Stopping current version...
cd %project_path%
call %mypath%\_kill.cmd

echo Set MASCOPE environment...
FOR /F "eol=# tokens=*" %%i IN (%~dp0.env) DO SET %%i

echo ** Installing latest version...
copy /y %mypath%\.env %project_path%\.env
cd %project_path%
call %mypath%\_install.cmd

echo ** Starting latest version...
cd %project_path%
call %mypath%\_start.cmd
