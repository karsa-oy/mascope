FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Environment setup
ENV MASCOPE_PATH=/app
ENV MASCOPE_TIMEZONE=Etc/UTC
ENV PATH=/root/.local/bin:$PATH
RUN ln -snf /usr/share/zoneinfo/$MASCOPE_TIMEZONE /etc/localtime && echo $MASCOPE_TIMEZONE > /etc/timezone

# Install system dependencies
RUN apt update && apt install -y \
    # Build tools for Python packages
    wget \
    build-essential \
    cmake \
    # jemalloc to avoid DLL segfaults
    libjemalloc2 \
    && rm -rf /var/lib/apt/lists/*

# Install PostgreSQL client for the db_init container.
# Pinned to major 16 to match the postgres:16-alpine server image in
# docker-compose*.yaml. The client major MUST NOT exceed the server major:
# pg_dump's custom-format archive is forward-only, so a newer pg_dump (e.g. the
# unpinned `postgresql-client` meta-package, which now resolves to PG18) writes
# an archive header (v1.16) that the server's older pg_restore cannot read
# ("unsupported version in file header"). Bump this in lockstep if the postgres
# image major is upgraded.
RUN wget -qO /etc/apt/keyrings/pgdg.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    && echo "deb [signed-by=/etc/apt/keyrings/pgdg.asc] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && apt update \
    && apt install -y postgresql-client-16 \
    && rm -rf /var/lib/apt/lists/*

# use jemalloc to avoid DLL segfaults (free(): invalid pointer)
ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2

# .NET runtime is only needed for the optional Thermo RawFileReader backend
# (MASCOPE_THERMO_BACKEND=thermo). The default OpenTFRaw backend needs nothing
# extra, so .NET is skipped unless the image is built with INSTALL_DOTNET=true.
ARG INSTALL_DOTNET=false
RUN if [ "$INSTALL_DOTNET" = "true" ]; then \
        wget https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb -O packages-microsoft-prod.deb \
        && dpkg -i packages-microsoft-prod.deb \
        && rm packages-microsoft-prod.deb \
        && apt update \
        && apt install -y dotnet-runtime-9.0 \
        && rm -rf /var/lib/apt/lists/*; \
    fi

WORKDIR /app

# Set production runtime state
# NOTE: MASCOPE_ENV environment variable will override env.active at runtime
# The state.json provides defaults, actual env comes from docker-compose
RUN mkdir .runtime
RUN echo '{"env":{"active":"prod","override":null},"mode":{"active":"prod","override":null}}' >> ./.runtime/state.json

# Copy entire workspace (required for uv tool install to resolve dependencies)
ADD . .

# Install Mascope backend and all workspace dependencies
# This creates the mascope-backend console script in /root/.local/bin
RUN uv tool install .

# Launch backend service
# Docker-compose overrides with specific service names: "api-server" or "file-converter"
ENTRYPOINT ["mascope-backend", "run"]