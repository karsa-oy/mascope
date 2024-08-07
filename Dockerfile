# FRONTEND BUILDER
FROM node:22-alpine as frontend-build

COPY ./frontend ./

RUN npm install
RUN npm run build

# BACKEND BUILDER
FROM python:3.12-bookworm as backend-build

# setup tooling

RUN pip install poetry

# setup directories

WORKDIR /app

# build libraries
WORKDIR /app/libraries/mascope_runtime
COPY ./libraries/mascope_runtime .
RUN poetry build

WORKDIR /app/libraries/mascope_hardware
COPY ./libraries/mascope_hardware .
RUN poetry build

WORKDIR /app/libraries/mascope_lib
COPY ./libraries/mascope_lib .
RUN poetry build

# build and install backend

WORKDIR /app/backend
RUN poetry config virtualenvs.in-project true
COPY ./backend/ .
RUN poetry install

FROM python:3.12-alpine

RUN apk update
RUN apk add nginx

WORKDIR /app

# RUN addgroup -g 1000 app
# RUN adduser app -h /app -u 1000 -G 1000 -DH
# USER 1000

# copy build outputs

COPY --from=frontend-build /dist /app/frontend/
COPY --from=backend-build /app /app

# run

ENTRYPOINT ["/app/backend/.venv/bin/mascope-api"]
