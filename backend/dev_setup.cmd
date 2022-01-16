@echo off
setlocal EnableDelayedExpansion

REM   Backend services development setup with python venv or miniconda;
REM   Prerequisites:  python version >3.6 and <3.9 installed;

if defined CONDA_EXE (
  call :conda_here
) else (
  call :venv_here
)

echo ========================
echo   2. Install karsalib package:
echo ========================
  pip install -e karsalib || goto :error

echo ========================
echo   3. Install hw_interfaces package:
echo ========================
  pip install -e hw_interfaces || goto :error

echo ========================
echo   4. Install karsaimg package:
echo ========================
  pip install -e karsaimg || goto :error

echo ========================
echo   5. Install scenthound package:
echo ========================
  pip install -e scenthound || goto :error

echo ========================
echo   6. Install backend services:
echo ========================
  pip install -e router_service || goto :error
  pip install -e tof_service || goto :error
  pip install -e services || goto :error

  pip install py-spy || goto :error

echo ========================
echo   7. Dev setup for backend is done.
echo. 
echo   8. To start the services, run the script:
echo     run_services.cmd
echo ========================
  exit /b 0


:conda_here
echo ========================
echo   1. Create development setup in conda environment:
echo ========================
  exit /b 0


:venv_here
echo ========================
echo   1. Create and activate virtual environment:
echo ========================
rem  python -m venv .venv || goto :error
  call .venv\Scripts\activate || goto :error
  pushd src
  exit /b 0


:error
set err=%ERRORLEVEL%
echo ========================
echo Failed with error %err%
echo ========================
exit /b %err%