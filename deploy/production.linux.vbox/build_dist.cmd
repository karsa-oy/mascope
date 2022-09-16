@echo off
set mypath=%~dp0
set frontend_path=%mypath%\..\..\frontend

echo Set MASCOPE environment...
pushd %mypath%
FOR /F "eol=# tokens=*" %%i IN (%~dp0.env) DO SET %%i
popd

echo Build MASCOPE dist package...
pushd %frontend_path%
call yarn build
popd

echo Find new MASCOPE UI distribution package in frontend/dist

exit /b 0
