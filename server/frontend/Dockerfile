# This image is built from the REPO ROOT (see docker-compose.yaml
# frontend.build.context) so it can reach both server/frontend and the
# docs/ tree. Paths below are therefore relative to the repo root.

# FRONTEND BUILDER
FROM node:22-alpine AS frontend-build

ARG MASCOPE_RUNTIME

WORKDIR /app

# Bake the runtime name in before the copy so a build-context .env.production
# (a developer's local override) still wins, matching the previous behaviour.
RUN echo "MASCOPE_RUNTIME='${MASCOPE_RUNTIME}'" >> .env.production

# build frontend
COPY server/frontend/ ./
RUN npm install
RUN npm run build

# DOCS BUILDER
# Render the user documentation (docs/user) to static HTML. --strict fails the
# build on broken links, so a bad doc link breaks the image, not just CI.
FROM python:3.12-alpine AS docs-build

WORKDIR /docs-src

RUN pip install --no-cache-dir "mkdocs-material>=9.7,<10"

COPY mkdocs.yml ./
COPY docs ./docs
RUN mkdocs build --strict   # outputs to ./site

# RUNTIME
FROM nginx:1.27-alpine

# set timezone
ENV MASCOPE_TIMEZONE=Etc/UTC
RUN ln -snf /usr/share/zoneinfo/$MASCOPE_TIMEZONE /etc/localtime && echo $MASCOPE_TIMEZONE > /etc/timezone

WORKDIR /app

ENV MASCOPE_PATH=/app

# copy build outputs
COPY --from=frontend-build /app/dist /app/frontend/

# the rendered docs site, served by nginx at /docs/
COPY --from=docs-build /docs-src/site /app/docs/

# stage both nginx configs; the entrypoint picks one based on MASCOPE_TLS
COPY server/frontend/nginx.conf /etc/nginx/mascope/nginx.conf
COPY server/frontend/nginx.http.conf /etc/nginx/mascope/nginx.http.conf
COPY server/frontend/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# SERVE API & FRONTEND (HTTPS by default; MASCOPE_TLS=off serves HTTP on :80)
CMD ["/docker-entrypoint.sh"]
