@echo off

pushd backend
start "mascope-backend" cmd /k poetry run server
popd
pushd frontend
start "mascope-frontend" cmd /k yarn serve --host
popd

pushd backend
start "mascope-backend-file-converter-kltof1" cmd /k poetry run file-converter --config ./backend/service/file_converter_config/kltof1.yaml
popd
pushd backend
start "mascope-backend-file-converter-kltof2" cmd /k poetry run file-converter --config ./backend/service/file_converter_config/kltof2.yaml
popd
pushd backend
start "mascope-backend-file-converter-korbi1" cmd /k poetry run file-converter --config ./backend/service/file_converter_config/korbi1.yaml
popd