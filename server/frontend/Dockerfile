# FRONTEND BUILDER
FROM node:22-alpine AS frontend-build

ARG MASCOPE_RUNTIME

RUN echo "MASCOPE_RUNTIME='${MASCOPE_RUNTIME}'" >> .env.production

# build frontend
COPY . ./
RUN npm install
RUN npm run build

# RUNTIME
FROM nginx:1.27-alpine

# set timezone
ENV MASCOPE_TIMEZONE=Etc/UTC
RUN ln -snf /usr/share/zoneinfo/$MASCOPE_TIMEZONE /etc/localtime && echo $MASCOPE_TIMEZONE > /etc/timezone

WORKDIR /app

ENV MASCOPE_PATH=/app

# copy build outputs
COPY --from=frontend-build /dist /app/frontend/

# stage both nginx configs; the entrypoint picks one based on MASCOPE_TLS
COPY ./nginx.conf /etc/nginx/mascope/nginx.conf
COPY ./nginx.http.conf /etc/nginx/mascope/nginx.http.conf
COPY ./docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# SERVE API & FRONTEND (HTTPS by default; MASCOPE_TLS=off serves HTTP on :80)
CMD ["/docker-entrypoint.sh"]