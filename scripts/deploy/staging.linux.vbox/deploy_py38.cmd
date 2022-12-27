@echo off
set mypath=%~dp0

pushd %mypath%
call build_dist.cmd
pushd py38
vagrant halt
vagrant up --provision
popd
popd

exit /b 0
