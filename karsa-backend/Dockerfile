FROM python:3.8-slim

# configure tmux setup for launching services
RUN apt-get update -y && apt-get install -y tmux
RUN pip install tmuxp
COPY .bashfuncs .bashfuncs
COPY .tmux.conf /root/.tmux.conf
RUN echo "source .bashfuncs" >> /root/.bash_profile

# create directories
RUN mkdir -p /karsa-backend
WORKDIR /karsa-backend
RUN mkdir -p ./Projects ./TofDaq

# install external dependencies
COPY ./src/external-requirements.txt .
RUN pip install --no-cache-dir -r external-requirements.txt

# setup karsa backend
COPY . .
WORKDIR /karsa-backend/src
RUN pip install --no-cache-dir -r internal-requirements.txt

# launch services
WORKDIR /karsa-backend
ENTRYPOINT [ "tmuxp", "load", "." ]