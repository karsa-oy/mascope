@echo off
pushd backend
poetry install --no-interaction --no-root
popd
pushd frontend
npm install
popd
