FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Environment setup
ENV MASCOPE_PATH=/app
ENV MASCOPE_TIMEZONE=Europe/Helsinki
ENV PATH=/root/.local/bin:$PATH
RUN ln -snf /usr/share/zoneinfo/$MASCOPE_TIMEZONE /etc/localtime && echo $MASCOPE_TIMEZONE > /etc/timezone

# Install system dependencies
RUN apt update && apt install -y \
    # Build tools for Python packages
    wget \
    build-essential \
    cmake \
    # PostgreSQL client (for db_init container)
    postgresql-client \
    # jemalloc to avoid DLL segfaults
    libjemalloc2 \
    && rm -rf /var/lib/apt/lists/*


# use jemalloc to avoid DLL segfaults (free(): invalid pointer)
ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2

# Install .NET runtime (required for ThermoFisher library)
RUN wget https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb -O packages-microsoft-prod.deb \
    && dpkg -i packages-microsoft-prod.deb \
    && rm packages-microsoft-prod.deb \
    && apt update \
    && apt install -y dotnet-runtime-9.0 \
    && rm -rf /var/lib/apt/lists/*

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