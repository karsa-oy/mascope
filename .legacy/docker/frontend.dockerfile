FROM node:18

RUN apt-get update -y && apt-get install -y xdg-utils

RUN mkdir -p /frontend
WORKDIR /frontend
COPY . .
RUN yarn install

ENTRYPOINT [ "yarn", "serve" ]

