FROM node:12

# python 3.6 is needed for some dependencies
RUN wget https://www.python.org/ftp/python/3.6.3/Python-3.6.3.tar.xz && \
    tar xJf Python-3.6.3.tar.xz && \
    cd Python-3.6.3 && \
    ./configure && \
    make && \
    make install
ENV PYTHON /usr/bin/python3.6

# other electron dependencies
RUN apt-get update -y && apt-get install \
    git libx11-xcb1 libxcb-dri3-0 libxtst6 libnss3 \
    libatk-bridge2.0-0 libgtk-3-0 libxss1 libasound2 \
    build-essential \
    -yq --no-install-suggests --no-install-recommends \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# copy frontend code
RUN mkdir -p /karsa-electron
WORKDIR /karsa-electron
COPY . .
RUN chown -R node /karsa-electron

USER node
RUN npm install yarn
RUN yarn install
RUN npx electron-rebuild

# Electron needs root for sand boxing
# see https://github.com/electron/electron/issues/17972
USER root
RUN chown root /karsa-electron/node_modules/electron/dist/chrome-sandbox
RUN chmod 4755 /karsa-electron/node_modules/electron/dist/chrome-sandbox

USER node
ENTRYPOINT [ "yarn", "electron:serve", "--no-sandbox" ]