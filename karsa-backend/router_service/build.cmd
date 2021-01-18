@echo off

call python setup.py bdist_wheel  || exit /b %errorlevel%
