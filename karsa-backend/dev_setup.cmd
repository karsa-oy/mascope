@echo off
setlocal EnableDelayedExpansion

REM   Backend services development setup (created in virtual environment);
REM   Prerequisits:  python version > 3.6 and virtualenv installed;

echo ========================
echo   1. Create and activate virtual environment (this step can be skipped):
echo ========================
  virtualenv .venv || goto :error
  call .venv\Scripts\activate || goto :error

echo ========================
echo   2. Install hw_interfaces package:
echo ========================
  pip install -e hw_interfaces || goto :error

echo ========================
echo   3. Install other dependencies for the backend services:
echo ========================
  pip install -r router_service\router_service\requirements.txt || goto :error
  pip install -r tof_service\tof_service\requirements.txt || goto :error
  pip install -r services\services\requirements.txt || goto :error

echo ========================
echo   4. Dev setup for karsa-backend-services is done.
echo. 
echo   5. To start the services, run the following instructions:
echo     .venv\Scripts\activate
echo     run_services.cmd
echo ========================

  exit /b 0


:error
set err=%ERRORLEVEL%
echo ========================
echo Failed with error %err%
echo ========================
exit /b %err%