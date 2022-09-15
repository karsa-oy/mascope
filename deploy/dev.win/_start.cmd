@echo off

pushd backend
start "mascope-backend" cmd /k poetry run server
popd
pushd frontend
start "mascope-frontend" cmd /k yarn serve --host
popd
