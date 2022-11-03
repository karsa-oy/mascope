@echo off
set mypath=%~dp0

pushd %mypath%
call build_dist.cmd
vagrant reload --provision
popd

exit /b 0
