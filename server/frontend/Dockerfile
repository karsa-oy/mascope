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

# copy nginx config
COPY ./nginx.conf /etc/nginx/conf.d/nginx.conf

# SERVE API & FRONTEND
CMD nginx -g 'daemon off;'