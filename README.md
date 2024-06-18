# Mascope

### Description

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

### Deploy for development (Windows)

1. Install prerequisites:

   - [Python 3.10](https://www.python.org/downloads/release/python-31011/) - Python interpreter
   - [Poetry](https://python-poetry.org/) - Python dependency manager
   - [Node 22](https://nodejs.org/en) - JavaScript runtime environment

2. Set up deployment environment by creating file `/scripts/deploy/dev.win/.debug_env`, with the following contents (example, note that the specified directories must exist):

```
MASCOPE_PRIVATE_DATABASE_DIR=C:/mascope_data/database
MASCOPE_PRIVATE_INSTRUMENT_DIR=C:/mascope_data/instrument
```

3. Run `/scripts/deploy/dev.win/deploy.cmd`. This will install and run the application (frontend and backend).

4. Setup Playwright for frontend tests:

```
cd ./frontend
npx playright install
```
