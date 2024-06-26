### Build production version of mascope bundle (backend, frontend, file services...)

#### Get build environment ready:

- `frontend_setup` folder contains stuff, which overrides the one from `/frontend/scripts/build`;
- `backend_setup` folder contains stuff, which overrides the one from `/backend/scripts/build`;
- `setup` folder may contain `.env`, which overrides those from frontend and backend build configurations;
- follow file-naming conventions to enable the override protocol work properly;

#### Build mascope bundle:

- build is done on Windows host with dev.environment installed for the whole project (frontend+backend);
- run `build.cmd`; resulting `./mascope_bundle.tar.gz` contains frontend/backend packages and a bundle setup;
- **NOTE: All scripts and `.env` file must have `LF` line endings to correctly work on Linux**

#### Deploy mascope bundle:

- deliver the bundle tar to a target (supposed to be put to the target `~/shared` directory);
- in the first installation, untar the bundle archive and run `./setup.sh`
- next time use `mascope-install` script to deploy next versions, delivered to the same place;
- **NOTE: If the `.env` file for a particular deployment target changes, the old one must be deleted from `~/.local/bin` prior to running `mascope-install`**
