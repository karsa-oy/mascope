FROM python:3.8-slim

# configure tmux setup for launching services
RUN apt-get update -y && apt-get install -y tmux
RUN pip install tmuxp poetry
COPY docker/.tmux.conf /root/.tmux.conf
COPY docker/.bash_profile /root/.bash_profile

# create directories
RUN mkdir -p /backend
WORKDIR /backend

# leverage docker caching to optimize builds,
#  i.e. install dependencies in one layer...
COPY poetry.lock pyproject.toml ./
RUN poetry install --no-interaction  --no-root -vvv
#  ...and the actual package in a seperate layer!
COPY . .
RUN poetry install --no-interaction -vvv

# launch services
ENTRYPOINT [ "tmuxp", "load", "docker/.tmuxp.yml" ]