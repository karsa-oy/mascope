@echo off
set mypath=%~dp0
set project_path=%~dpnx1

echo ** Stopping current version...
cd %project_path%
call %mypath%\_kill.cmd

echo ** Installing latest version...
copy /y %mypath%\.env %project_path%\.env
cd %project_path%
call %mypath%\_install.cmd

echo ** Starting latest version...
cd %project_path%
call %mypath%\_start.cmd
