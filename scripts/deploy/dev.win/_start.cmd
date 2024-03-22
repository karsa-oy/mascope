@echo off

pushd backend
start "mascope-backend" cmd /k poetry run mascope-api
popd
pushd frontend
start "mascope-frontend" cmd /k npm run dev
popd

@REM pushd backend
@REM start "mascope-backend-file-converter-kltof1" cmd /k poetry run file-converter --config ./backend/service/file_converter_config/KLTOF1.yaml
@REM popd
@REM pushd backend
@REM start "mascope-backend-file-converter-kltof2" cmd /k poetry run file-converter --config ./backend/service/file_converter_config/KLTOF2.yaml
@REM popd
@REM pushd backend
@REM start "mascope-backend-file-converter-korbi1" cmd /k poetry run file-converter --config ./backend/service/file_converter_config/KORBI1.yaml
@REM popd