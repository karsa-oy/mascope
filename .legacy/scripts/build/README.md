# Mascope build/deploy infrastructure

## Description

Mascope build configurations are stored in directories specific to the deployment target. These are stored in git.

After installed, Mascope persistently keeps its config in the resulting `.env` file:

- Windows (development): in the project root
- Linux (staging/production): in `$HOME/.local/bin/.env`

The `.env` file is overwritten after each reinstall. The `.env` matters for Mascope restart.

```
mascope
├───agents
├───backend
├───frontend
└───scripts                # Build and deployment scripts
    ├───build                 # Build scripts
    │   ├───production.linux     # Example deployment configuration
    │   └───<target>             # Target specific deployment configuration
    └───deploy                # Deployment scripts
        ├───dev.win              # Windows deployment (development)
        └───staging.linux.vbox   # Linux virtualbox deployment (staging)
```

## Build

The build environment must be configured according to the specifics of the deployment target.

The run script `mascope-run-backend` must be edited to start the desired backend services. The respective configuration files must be provided in `/backend_setup/config`.

Environment variables for the deployment target must be configured in `/setup/.env`.

Build is done on a Windows host with the development environment installed. Run `<target>/build.cmd`, resulting tar archive contains the Mascope distribution package.

**NOTE: In order to be able to run the build script, one must have added `/Git/usr/bin` to the Windows environment variable `PATH`.**

## Deployment

To deploy development version of Mascope on Windows, run `/scripts/deploy/dev.win/deploy.cmd`. To deploy staging version of Mascope on Linux (virtual box), refer to the README under `/deploy/staging.linux.vbox`.

For debug purposes one may need to modify `.env` values. To avoid git complaints, parallel `.debug_env` files are introduced. Their values override those from corresponding `.env`. They are git-ignored.
