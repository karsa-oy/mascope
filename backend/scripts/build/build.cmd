@echo off
setlocal EnableDelayedExpansion
:: Syntax: build [env_file] [setup_dir]
:: if no args, then env_file=./setup/.env and setup_dir=./setup

set mypath=%~dp0
call :get_full_path %mypath%\..\..
set backend_path=!last_result!
set my_setup_dir=%mypath%\setup
set setup_dir=%mypath%\setup
set env_file=%mypath%\setup\.env

if not [%1]==[] (
    call :get_full_path %1
    set env_file=!last_result!
)
if not [%2]==[]  (
    call :get_full_path %2
    set setup_dir=!last_result!
)
echo Using:
echo env_file=%env_file%
echo setup_dir=%setup_dir%

echo Set MASCOPE environment...
IF NOT EXIST %env_file% (echo Error: missing %env_file% & exit /b 1)
FOR /F "eol=# tokens=*" %%i IN (%env_file%) DO SET %%i

echo Build MASCOPE backend package...
pushd %backend_path%
call poetry update
call poetry build

rm -r -f mascope_backend
mkdir mascope_backend

mv dist/*.whl mascope_backend\ || (echo Error finding .whl & exit /b 1)
xcopy /s /y %my_setup_dir%\*.* mascope_backend\
xcopy /s /y %setup_dir%\*.* mascope_backend\
copy /y %env_file% mascope_backend\
tar -c -z -f mascope_backend.tar.gz mascope_backend || (echo Error archiving mascope_backend & exit /b 1)
rm -r -f mascope_backend
echo Find new mascope_backend distribution package in %backend_path%\mascope_backend.tar.gz
popd

echo Backend build configuration:
echo MASCOPE_PUBLIC_MODE = %MASCOPE_PUBLIC_MODE%
echo MASCOPE_PUBLIC_HOST = %MASCOPE_PUBLIC_HOST%
echo MASCOPE_PUBLIC_PORT = %MASCOPE_PUBLIC_PORT%
echo MASCOPE_PUBLIC_API_PORT = %MASCOPE_PUBLIC_API_PORT%
echo MASCOPE_PRIVATE_ENV = %MASCOPE_PRIVATE_ENV%
echo MASCOPE_PRIVATE_DATADIR = %MASCOPE_PRIVATE_DATADIR%

exit /b 0


:get_full_path
set last_result=%~f1
exit /b 0
