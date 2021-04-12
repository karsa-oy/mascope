@echo off

:: Activate virtual environment
call ..\.venv\Scripts\activate || goto :error

:: Build
python -m pip install wheel
call python setup.py bdist_wheel  || exit /b %errorlevel%
deactivate
