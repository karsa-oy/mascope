# Mascope

## Overview

This monorepo contains Mascope python backend and Vue frontend, as well as peripheral "agent" applications and build/deploy scripts. For more details on these, refer to their respective READMEs.

The project is structured as follows:

```
mascope/        # Project root
├───agents/          # Instrument machine agents
│   ├───file_mover          # File mover (for Orbitrap)
│   ├───ht300a              # Autosampler
│   └───tof_agent           # Tofwerk TOF
├───backend/         # App backend (Python, FastAPI, SQLite)
├───frontend/        # App frontend (Javascript, Vue, PrimeVue)
├───libraries/       # Shared libraries
│   ├───mascope_api/        # Public REST API wrapper
│   ├───mascope_hardware/   # Internal hardware library
│   ├───mascope_lib/        # Internal general library
├───notebooks/        # Jupyter dev environment
├───scripts/          # Build and deploy scripts
└───.legacy/          # Deprecated code and docs
```

The backend and frontend have their own setup documentation for Windows and Linux, using scripts and virtualbox. In addition to these setup methods, the frontend and backend are Dockerized; see the _Quick start with Docker_ section for more information.

![Mascope architecture diagram](.legacy/docs/assets/mascope_sw_architecture.png "Mascope architecture diagram")

## Windows Development Environment

The only prerequisite is [Powershell 7](https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell-on-windows), which should be available on Windows 11 by default.

To install your development environment, simply run:

```
> .\scripts\windows_dev_setup.ps1
```

The script will install _Python 3.12_, _Node 22_, _Pipx_ and _Poetry_, as well as dependencies for all our packages and the `mascope` cli.

After installation, run `mascope --help` for usage instructions.
