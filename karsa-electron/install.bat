@ECHO OFF
ECHO Installing Karsa project in Development mode.
ECHO ------------------------------------------------

IF NOT EXIST py_code (
    mkdir py_code
    ECHO Installing Karsa backend.
    REM git clone https://bitbucket.org/kausiala/karsa2020.git py_code || goto :error
    git clone git@bitbucket.org:kausiala/karsa2020.git py_code || goto :error
) ELSE (
    ECHO Refresh Karsa backend.
    pushd py_code
    git stash
    git pull || goto :error
    git stash pop
    popd
)
ECHO Copy env file from python repo to here to share same configurations
COPY py_code\.env .env || goto :error

IF NOT EXIST py (
    ECHO Install portable python
    pushd tools
    unzip.exe "Portable Python-3.8.2 x64.zip" || goto :error
    move "Portable Python-3.8.2 x64" ..\py || goto :error
    popd 
)

ECHO Install python requirements
pushd py_code
..\py\App\python\python.exe -m pip install --no-warn-script-location -r requirements.txt || goto :error
popd
ECHO Finished installation of python with packages

ECHO Installing Electron environment and JS dependencies.
call yarn install || goto :error
ECHO Finished installation of Electron environment and JS dependencies..
ECHO ------------------------------------------------
ECHO Success!
exit /b 0

:error
git stash pop
ECHO Operation failed!
exit /b 1
