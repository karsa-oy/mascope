FROM python:3.8-slim


RUN apt-get update -y

# install mono - https://www.mono-project.com/
# to enable .NET bindings in pythonnet (a.k.a clr) - https://github.com/pythonnet/pythonnet
RUN apt-get install -y apt-transport-https dirmngr gnupg ca-certificates && \
  apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF && \
  (echo "deb https://download.mono-project.com/repo/debian stable-buster main" | tee /etc/apt/sources.list.d/mono-official-stable.list) && \
  apt-get update
RUN apt-get install -y mono-devel gcc g++

# configure tmux setup for launching services
RUN apt-get install -y tmux
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