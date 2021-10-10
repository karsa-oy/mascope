#!/usr/bin/env bash

(cd ./karsa-backend/src; ./build-requirements.sh)
docker-compose build