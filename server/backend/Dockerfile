FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# environment
ENV MASCOPE_PATH=/app
ENV MASCOPE_TIMEZONE=Europe/Helsinki
ENV PATH=/root/.local/bin:$PATH
RUN ln -snf /usr/share/zoneinfo/$MASCOPE_TIMEZONE /etc/localtime && echo $MASCOPE_TIMEZONE > /etc/timezone

# build utils
RUN apt update
RUN apt install -y wget build-essential cmake

# use jemalloc to avoid DLL segfaults (free(): invalid pointer)
RUN apt install --yes --no-install-recommends libjemalloc2
ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2

# dotnet runtime
RUN wget https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb -O packages-microsoft-prod.deb \
    && dpkg -i packages-microsoft-prod.deb \
    && rm packages-microsoft-prod.deb \
    && apt update \
    && apt install -y dotnet-runtime-9.0

WORKDIR /app

RUN mkdir .runtime
RUN echo '{"env":{"active":"prod","override":null},"mode":{"active":"prod","override":null}}' >> ./.runtime/state.json

ADD . .

# set prod runtime state

# install mascope-backend entrypoint
RUN uv tool install .

# launch service
ENTRYPOINT ["mascope-backend", "run"]
