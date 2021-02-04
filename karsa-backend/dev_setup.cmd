@echo off
setlocal EnableDelayedExpansion

REM   Backend services development setup (created in virtual environment);
REM   Prerequisites:  python version >3.6 and <3.9 installed;

echo ========================
echo   1. Create and activate virtual environment:
echo ========================
  python -m venv .venv || goto :error
  call .venv\Scripts\activate || goto :error

echo ========================
echo   2. Install hw_interfaces package:
echo ========================
  pip install -e hw_interfaces || goto :error

echo ========================
echo   3. Install karsalib package:
echo ========================
  pip install -e karsalib || goto :error

echo ========================
echo   4. Install backend services:
echo ========================
  pip install -e router_service || goto :error
  pip install -e tof_service || goto :error
  pip install -e services || goto :error

echo ========================
echo   5. Dev setup for karsa-backend is done.
echo. 
echo   6. To start the services, run the script:
echo     run_services.cmd
echo ========================

  exit /b 0


:error
set err=%ERRORLEVEL%
echo ========================
echo Failed with error %err%
echo ========================
exit /b %err%