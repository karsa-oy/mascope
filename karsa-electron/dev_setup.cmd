@echo off

echo ======================================================
echo Installing karsa-electron project in development mode.
echo ======================================================

call yarn install || goto :error

echo ========
echo Success!
echo ========
exit /b 0

:error
set err=%ERRORLEVEL%
echo ========================
echo Failed with error %err%
echo ========================
exit /b %err%