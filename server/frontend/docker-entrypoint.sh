#!/bin/sh
# Select the nginx config at container start based on MASCOPE_TLS.
#
#   MASCOPE_TLS=on  (default) -> HTTPS on :443 (needs ssl_* secrets)  [nginx.conf]
#   MASCOPE_TLS=off           -> HTTP on :80 for localhost            [nginx.http.conf]
#
# Defaulting to HTTPS keeps existing prod deployments unchanged.
set -e

# Drop the base image's default server so it cannot clash on :80.
rm -f /etc/nginx/conf.d/default.conf

if [ "${MASCOPE_TLS:-on}" = "off" ]; then
  echo "MASCOPE_TLS=off -> serving over HTTP (localhost only)"
  cp /etc/nginx/mascope/nginx.http.conf /etc/nginx/conf.d/nginx.conf
else
  if [ ! -s /run/secrets/ssl_certificate ] || [ ! -s /run/secrets/ssl_secret_key ]; then
    echo "ERROR: MASCOPE_TLS is on but the SSL certificate/key secret is missing or empty." >&2
    echo "       Generate one with 'mascope cert gen', or set MASCOPE_TLS=off for a localhost HTTP trial." >&2
    exit 1
  fi
  cp /etc/nginx/mascope/nginx.conf /etc/nginx/conf.d/nginx.conf
fi

exec nginx -g 'daemon off;'
