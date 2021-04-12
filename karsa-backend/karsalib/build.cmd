@echo off

:: Activate virtual environment
call ..\.venv\Scripts\activate || goto :error

:: Build
python -m pip install wheel twine
call python setup.py bdist_wheel  || goto :error
call twine check dist/*  || goto :error
deactivate
exit /b 0

:error
set err=%ERRORLEVEL%
echo ========================
echo Failed with error %err%
echo ========================
exit /b %err%
