# FRONTEND
FROM node:22-alpine as frontend

COPY ./frontend ./
RUN npm run build

# BACKEND
FROM python:3.12-bookworm

RUN pip install uv

RUN mkdir -p /server
WORKDIR /server

COPY --from=frontend /dist ./frontend/
COPY ./backend/ ./

# installation
RUN uv venv --python python3.12
RUN uv pip install .

ENTRYPOINT ["mascope-api"]
