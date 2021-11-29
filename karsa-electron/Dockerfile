FROM node:12

# setup python 3.6
# this is needed for some electron dependencies
RUN wget https://www.python.org/ftp/python/3.6.3/Python-3.6.3.tar.xz && \
    tar xJf Python-3.6.3.tar.xz && \
    cd Python-3.6.3 && \
    ./configure && \
    make && \
    make install
ENV PYTHON /usr/bin/python3.6

# setup electron dependencies
RUN apt-get update -y && apt-get install \
    git libx11-xcb1 libxcb-dri3-0 libxtst6 libnss3 \
    libatk-bridge2.0-0 libgtk-3-0 libxss1 libasound2 \
    build-essential \
    -yq --no-install-suggests --no-install-recommends \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# create directories
RUN mkdir -p /karsa-electron && chown node /karsa-electron
WORKDIR /karsa-electron

# setup karsa frontend
COPY --chown=node:node . .
USER node
RUN npm install yarn && \
    yarn install && \
    npx electron-rebuild

# fix fs/promises in ./node_modules/electron-updater/out/AppUpdater.js
# see https://github.com/electron-userland/electron-builder/issues/6000
# can probably be removed after updating to node 14
RUN patch --ignore-whitespace \
  ./node_modules/electron-updater/out/AppUpdater.js electron-updater.patch

# Electron needs root for sand boxing
# see https://github.com/electron/electron/issues/17972
USER root
RUN chown root /karsa-electron/node_modules/electron/dist/chrome-sandbox && \
    chmod 4755 /karsa-electron/node_modules/electron/dist/chrome-sandbox

USER node
ENTRYPOINT [ "yarn", "electron:serve", "--no-sandbox", "--disable-gpu" ]