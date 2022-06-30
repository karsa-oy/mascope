@echo off

pushd ..
python -m poetry install

:error
set err=%ERRORLEVEL%
echo ========================
echo Failed with error %err%
echo ========================
exit /b %err%