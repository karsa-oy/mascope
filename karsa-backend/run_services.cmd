@echo off

if defined CONDA_EXE (
  echo Running karsa services in conda environment
) else (
  echo Running karsa services locally
  :: Activate virtual environment
  call .venv\Scripts\activate || goto :error
)

:: Start Router locally, if not already running
powershell Test-NetConnection 127.0.0.1 -p 5010 | find /i "failed" && start cmd /k karsa-router-service

:: Start TOFService
start cmd /k karsa-tof-service --ns=TofDaq || goto :error

:: Set working directory to virtual environment dir
pushd .venv || goto :error

:: Start other services
start cmd /k karsa-fileio-service --ns=TofDaq || goto :error
start cmd /k karsa-raw-streamer --config=../services/services/raw_streamer_config/h5.yaml || goto :error
start cmd /k karsa-fileio-service --ns=H5-data || goto :error
start cmd /k karsa-raw-streamer --config=../services/services/raw_streamer_config/raw.yaml || goto :error
start cmd /k karsa-fileio-service --ns=Orbitrap-data || goto :error
start cmd /k karsa-sample-service || goto :error
start cmd /k karsa-dataviz-service || goto :error
::start cmd /k karsa-signal-service || goto :error
popd

exit /b 0


:error
set err=%ERRORLEVEL%
echo Failed with error %err%
exit /b %err%