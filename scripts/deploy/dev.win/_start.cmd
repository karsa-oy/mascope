@echo off

pushd backend
start "mascope-backend" cmd /k poetry run mascope-api
popd
pushd frontend
start "mascope-frontend" cmd /k yarn serve --host
popd

pushd backend
start "mascope-backend-file-converter-kltof1" cmd /k poetry run file-converter --config ./backend/service/file_converter_config/KLTOF1.yaml
popd
pushd backend
start "mascope-backend-file-converter-kltof2" cmd /k poetry run file-converter --config ./backend/service/file_converter_config/KLTOF2.yaml
popd
pushd backend
start "mascope-backend-file-converter-korbi1" cmd /k poetry run file-converter --config ./backend/service/file_converter_config/KORBI1.yaml
popd

pushd backend
start "mascope-backend-file-downloader-kltof1" cmd /k poetry run file-downloader --config ./backend/service/file_downloader_config/KLTOF1.yaml
popd
pushd backend
start "mascope-backend-file-downloader-kltof2" cmd /k poetry run file-downloader --config ./backend/service/file_downloader_config/KLTOF2.yaml
popd
pushd backend
start "mascope-backend-file-downloader-korbi1" cmd /k poetry run file-downloader --config ./backend/service/file_downloader_config/KORBI1.yaml
popd