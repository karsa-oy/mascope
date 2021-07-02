@echo off

SET mypath=%~dp0
pushd %mypath%

if defined CONDA_EXE (
  echo Running unittests in conda environment
) else (
  echo Running unittests locally
  :: Activate virtual environment
  call ..\..\src\.venv\Scripts\activate || goto :error
)

python -m unittest discover -v || goto :error

popd
exit /b 0


:error
popd
set err=%ERRORLEVEL%
echo Failed with error %err%
exit /b %err%