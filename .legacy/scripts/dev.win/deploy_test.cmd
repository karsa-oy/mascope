@echo off
set mypath=%~dp0

pushd %mypath%
_deploy_test.cmd ..\..\..
popd