#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'


openssl req \
    -x509 \
    -nodes \
    -subj "/CN=mascope.app" \
    -addext "subjectAltName=DNS:mascope.app" \
    -days 365 \
    -newkey rsa:2048 \
    -keyout "${MASCOPE_PATH}/secrets/mascope.app.key" \
    -out "${MASCOPE_PATH}/secrets/mascope.app.pem"
