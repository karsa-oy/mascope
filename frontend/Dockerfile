# FRONTEND BUILDER
FROM node:22-alpine AS frontend-build

ARG MASCOPE_RUNTIME

RUN echo "MASCOPE_RUNTIME='${MASCOPE_RUNTIME}'" >> .env.production

# generate self-signed certificate
RUN apk add openssl
RUN openssl \
    req -x509 \
    -nodes \
    -subj "/CN=mascope.com" \
    -addext "subjectAltName=DNS:mascope.com" \
    -days 90 \
    -newkey rsa:2048 -keyout /tmp/self-signed.key \
    -out /tmp/self-signed.crt

# build frontend
COPY . ./
RUN npm install
RUN npm run build

# RUNTIME
FROM nginx:1.27-alpine

# set timezone
ENV MASCOPE_TIMEZONE=Europe/Helsinki
RUN ln -snf /usr/share/zoneinfo/$MASCOPE_TIMEZONE /etc/localtime && echo $MASCOPE_TIMEZONE > /etc/timezone

WORKDIR /app

ENV MASCOPE_PATH=/app

# copy build outputs
COPY --from=frontend-build /dist /app/frontend/

# copy certificates
COPY --from=frontend-build /tmp/self-signed.key /etc/ssl/private
COPY --from=frontend-build /tmp/self-signed.crt /etc/ssl/certs

# copy nginx config
COPY ./nginx.conf /etc/nginx/conf.d/nginx.conf

# SERVE API & FRONTEND
CMD nginx -g 'daemon off;'