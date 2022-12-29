@echo off
set mypath=%~dp0
set frontend_path=%mypath%\..\..\..\frontend

echo Set MASCOPE environment...
pushd %mypath%
FOR /F "eol=# tokens=*" %%i IN (.env) DO SET %%i
if exist .debug_env (
    echo Override with MASCOPE debug environment...
    FOR /F "eol=# tokens=*" %%i IN (.debug_env) DO SET %%i
)
popd

echo Build MASCOPE dist package...
pushd %frontend_path%
call yarn build
popd

echo Find new MASCOPE UI distribution package in frontend/dist
echo Build configuration:
echo MASCOPE_PUBLIC_MODE = %MASCOPE_PUBLIC_MODE%
echo MASCOPE_PUBLIC_HOST = %MASCOPE_PUBLIC_HOST%
echo MASCOPE_PUBLIC_PORT = %MASCOPE_PUBLIC_PORT%
echo MASCOPE_PUBLIC_API_PORT = %MASCOPE_PUBLIC_API_PORT%
echo MASCOPE_PRIVATE_ENV = %MASCOPE_PRIVATE_ENV%
echo MASCOPE_PRIVATE_DATADIR = %MASCOPE_PRIVATE_DATADIR%

exit /b 0
