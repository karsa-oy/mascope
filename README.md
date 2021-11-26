### Description

This monorepo contains the Karsa Python backend and Karsa Electron frontend. For more details on these, refer to their respective READMEs.

The backend and frontend have their own setup documentation for Windows and Linux, using scripts and virtualbox. In addition to these setup methods, the frontend and backend are Dockerized; see the *quick start* section for more information.

### Quick Start with Docker

For a quick development setup with docker:

 1. *Install* dependencies `docker` and `docker-compose`;
 2. *Build* with `./docker-build.sh`; 
 3. *Run* with `docker-compose up`;

The build script wraps `docker-compose build` with an extra optimization step. For additonal reference, check out the [docker-compose docs](https://docs.docker.com/compose/).

### Lockfile

To update the lockfile without populating `/node_modules` locally, run:
    `npm install --package-lock-only; yarn import`