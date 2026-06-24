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
  cp /etc/nginx/mascope/nginx.conf /etc/nginx/conf.d/nginx.conf
fi

exec nginx -g 'daemon off;'
