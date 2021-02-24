@echo off

:: Activate virtual environment
call ..\.venv\Scripts\activate || goto :error

:: Build
call python setup.py bdist_wheel  || exit /b %errorlevel%
