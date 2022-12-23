@echo off
set mypath=%~dp0

pushd %mypath%
call build_dist.cmd
set VAGRANT_VAGRANTFILE=Vagrantfile_py38 && vagrant reload --provision
popd

exit /b 0
