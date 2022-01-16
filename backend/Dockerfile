FROM python:3.8-slim

# configure tmux setup for launching services
RUN apt-get update -y && apt-get install -y tmux
RUN pip install tmuxp
COPY .bashfuncs .bashfuncs
COPY .tmux.conf /root/.tmux.conf
RUN echo "source .bashfuncs" >> /root/.bash_profile

# create directories
RUN mkdir -p /backend
WORKDIR /backend
RUN mkdir -p ./workspaces ./TofDaq

# install external dependencies
COPY ./src/external-requirements.txt .
RUN pip install --no-cache-dir -r external-requirements.txt

# setup karsa backend
COPY . .
WORKDIR /backend/src
RUN pip install --no-cache-dir -r internal-requirements.txt

# launch services
WORKDIR /backend
ENTRYPOINT [ "tmuxp", "load", "." ]