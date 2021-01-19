@echo off

:: Activate virtual environment
call .venv\Scripts\activate

:: Start Router locally, if not already running
powershell Test-NetConnection 127.0.0.1 -p 5010 | find /i "failed" && start cmd /k karsa-router-service

:: Start TOFService
start cmd /k karsa-tof-service

:: Set working directory to virtual environment dir
pushd .venv

:: Start other services
start cmd /k karsa-file-service
start cmd /k karsa-dataviz-service
::start cmd /k python SignalProcessorService.py
popd
