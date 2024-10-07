@echo off
setlocal EnableDelayedExpansion
:: Syntax: build [env_file] [setup_dir]
:: if no args, then env_file=./setup/.env and setup_dir=./setup

set mypath=%~dp0
call :get_full_path %mypath%\..\..
set frontend_path=!last_result!
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

echo Build MASCOPE frontend package...
pushd %frontend_path%
call npm run build

rm -r -f mascope_ui
mkdir mascope_ui

mv dist mascope_ui\ || (echo Error finding dist & exit /b 1)
xcopy /s /y %my_setup_dir%\*.* mascope_ui\
xcopy /s /y %setup_dir%\*.* mascope_ui\
copy /y %env_file% mascope_ui\
tar -c -z -f mascope_ui.tar.gz mascope_ui || (echo Error archiving mascope_ui & exit /b 1)
rm -r -f mascope_ui
echo Find new mascope_ui distribution package in %frontend_path%\mascope_ui.tar.gz
popd

echo Build configuration:
echo MASCOPE_PUBLIC_MODE = %MASCOPE_PUBLIC_MODE%
echo MASCOPE_PUBLIC_PORT = %MASCOPE_PUBLIC_PORT%
echo MASCOPE_PUBLIC_API_PORT = %MASCOPE_PUBLIC_API_PORT%
echo MASCOPE_PRIVATE_ENV = %MASCOPE_PRIVATE_ENV%
echo MASCOPE_PRIVATE_DATABASE_DIR = %MASCOPE_PRIVATE_DATABASE_DIR%
echo MASCOPE_PRIVATE_INSTRUMENT_DIR = %MASCOPE_PRIVATE_INSTRUMENT_DIR%

exit /b 0


:get_full_path
set last_result=%~f1
exit /b 0
