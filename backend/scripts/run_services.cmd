@echo off

:: Start Router locally, if not already running
powershell Test-NetConnection 127.0.0.1 -p 5010 | find /i "failed" && start cmd /k poetry run router

:: Start other services
:: start cmd /k karsa-file-streamer --config=../services/services/file_streamer_config/h5_local.yaml  --transit || goto :error
:: start cmd /k karsa-file-streamer --config=../services/services/file_streamer_config/raw_local.yaml  --transit || goto :error

start cmd /k poetry run sample-service || goto :error
start cmd /k poetry run signal-service || goto :error
start cmd /k poetry run target-service || goto :error
start cmd /k poetry run visualization-service || goto :error

popd

exit /b 0


:error
set err=%ERRORLEVEL%
echo Failed with error %err%
exit /b %err%