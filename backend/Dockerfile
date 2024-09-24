# BACKEND BUILDER
FROM python:3.12-bookworm AS backend-build

RUN apt update

# setup tooling
RUN pip install poetry

# setup directories
WORKDIR /app

# build libraries

WORKDIR /app/runtime/lib
COPY ./runtime/lib .
RUN poetry build

WORKDIR /app/libraries/mascope_hardware
COPY ./libraries/mascope_hardware .
# patch the tofwerk dll
ARG TW_DLL_PATH="/app/libraries/mascope_hardware/mascope_hardware/tofwerk/lib/dlls/linux_x86_64"
RUN apt install patchelf 
RUN patchelf --force-rpath --set-rpath ${TW_DLL_PATH} "${TW_DLL_PATH}/libtwh5.so"
RUN poetry build

WORKDIR /app/libraries/mascope_lib
COPY ./libraries/mascope_lib .
RUN poetry build

# build and install backend
WORKDIR /app/backend
RUN poetry config virtualenvs.in-project true
COPY ./backend .
RUN poetry install


# RUNTIME
FROM python:3.12-bookworm

# set timezone
ENV MASCOPE_TIMEZONE=Europe/Helsinki
RUN ln -snf /usr/share/zoneinfo/$MASCOPE_TIMEZONE /etc/localtime && echo $MASCOPE_TIMEZONE > /etc/timezone

# mono
RUN apt install -y ca-certificates gnupg
RUN gpg --homedir /tmp \
    --no-default-keyring \
    --keyring /usr/share/keyrings/mono-official-archive-keyring.gpg \
    --keyserver hkp://keyserver.ubuntu.com:80 \
    --recv-keys 3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF
RUN echo "deb [signed-by=/usr/share/keyrings/mono-official-archive-keyring.gpg] https://download.mono-project.com/repo/ubuntu stable-focal main" | tee /etc/apt/sources.list.d/mono-official-stable.list
RUN apt update
RUN apt install -y mono-devel

WORKDIR /app

ENV MASCOPE_PATH=/app

# copy build outputs
COPY --from=backend-build /app /app

# set prod runtime state
WORKDIR /app/runtime
COPY ./runtime/lib/state.prod.json ./state.json

# SERVE API & FRONTEND

ENTRYPOINT ["/app/backend/.venv/bin/mascope-launch"]