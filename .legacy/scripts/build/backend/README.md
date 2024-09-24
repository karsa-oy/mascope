## Build production version of the Mascope backend

**NOTE: The preferable method to deploy Mascope is to install it as a bundle package. Refer to the README under `/scripts` in the monorepo root.**

```
build
├───setup                           # Configurations
│   ├───config                          # Service configurations
│   │   ├───file_converter_config           # File converter config files
│   │   └───file_downloader_config          # File downloader config files
│   ├───.env                            # Environment variable configuration
│   ├───mascope-run-backend             # Shell script to run Mascope backend
│   └───setup.sh                        # Shell script to install Mascope backend
└───build.cmd                       # Build script
```

### Configure the production environment

The build environment must be configured according to the specifics of the deployment target.

The run script `mascope-run-backend` must be edited to start the desired backend services. The respective configuration files must be provided in `/setup/config`.

Environment variables for the deployment target must be configured in `.env`.

### Build Mascope backend

- Build is done on a Windows host with the development environment installed.
- Run `build.cmd`, resulting tar archive contains the backend distribution package.

**NOTE: In order to be able to run the build script, one must have added `/Git/usr/bin` to the Windows environment variable `PATH`.**

### Deploy Mascope backend

- Untar the tar archive and run `setup.sh`.
- Run `mascope-run-backend` to start backend services.
- Check runtime logs in `$MASCOPE_PRIVATE_LOG_DIR`.
