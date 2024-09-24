## Build production version of Mascope frontend

**NOTE: The preferable method to deploy Mascope is to install it as a bundle package. Refer to the README under `/scripts` in the monorepo root.**

```
build
├───setup        # Configurations
│   ├───nginx       # Nginx configurations
│   ├───.env        # Environment variable configuration
│   └───setup.sh    # Shell script to install Mascope backend
└───build.cmd    # Build script
```

### Configure the production environment

The build environment must be configured according to the specifics of the deployment target.

- `.env` contains frontend parameters

### Build Mascope frontend

- Build is done on Windows host with development environment installed.
- Run `build.cmd`, the resulting tar archive contains the frontend package.

**NOTE: In order to be able to run the build script, one must have added `/Git/usr/bin` to the Windows environment variable `PATH`.**

### Deploy Mascope frontend

- Untar the tar archive and run `setup.sh`.
