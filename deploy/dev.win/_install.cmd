@echo off
pushd backend
poetry install --no-interaction --no-root
popd
pushd frontend
yarn install
popd
