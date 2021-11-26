FROM python:3.8-slim

RUN apt-get update -y && apt-get install -y tmux
RUN pip install tmuxp
COPY .bashfuncs .bashfuncs
COPY .tmux.conf /root/.tmux.conf
RUN echo "source .bashfuncs" >> /root/.bash_profile

RUN mkdir -p /karsa-backend

WORKDIR /karsa-backend
COPY ./src/external-requirements.txt .
RUN pip install --no-cache-dir -r external-requirements.txt

COPY . .

WORKDIR /karsa-backend/src

RUN pip install --no-cache-dir -r internal-requirements.txt

WORKDIR /karsa-backend
ENTRYPOINT [ "tmuxp", "load", "." ]