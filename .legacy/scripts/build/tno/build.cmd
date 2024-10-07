@echo off
setlocal EnableDelayedExpansion

set mypath=%~dp0
call :get_full_path %mypath%\..\..\..
set project_root=!last_result!
set frontend_path=%project_root%\frontend
set backend_path=%project_root%\backend

echo Build MASCOPE bundle package...

:: build frontend package
call %frontend_path%\scripts\build\build.cmd %mypath%\setup\.env %mypath%\frontend_setup
:: build backend package
call %backend_path%\scripts\build\build.cmd %mypath%\setup\.env %mypath%\backend_setup

rm -r -f mascope_bundle
mkdir mascope_bundle
mv %frontend_path%\mascope_ui.tar.gz mascope_bundle\ || (echo Error archiving mascope_ui & exit /b 1)
mv %backend_path%\mascope_backend.tar.gz mascope_bundle\ || (echo Error archiving mascope_backend & exit /b 1)
copy /y %mypath%\setup\*.* mascope_bundle\ || (echo Error archiving mascope setup & exit /b 1)
tar -c -z -f mascope_bundle.tar.gz mascope_bundle || (echo Error archiving mascope_bundle & exit /b 1)
rm -r -f mascope_bundle
echo Find new mascope_bundle distribution package in %mypath%\mascope_bundle.tar.gz

exit /b 0


:get_full_path
set last_result=%~f1
exit /b 0
