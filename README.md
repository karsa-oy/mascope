# Mascope

**A platform for analysing high-resolution mass spectrometry data** - import
instrument files, browse samples and batches, run targeted matching and
calibration, and explore results in the web UI or from Python.

<!--
TODO: add a screenshot or short GIF of the web UI here, e.g.:
![Mascope web UI](docs/assets/mascope-ui.png)
Drop the image at docs/assets/mascope-ui.png and uncomment the line above.
-->

Mascope ingests Thermo Orbitrap (`.raw`) and Tofwerk (TOF) data, processes it
through a calibration + peak-detection + targeted-matching pipeline, and serves
it through a multi-user web application and a Python SDK. It is built for
laboratories that need reproducible, high-throughput analysis of complex spectra.

## Try it in 5 minutes

Run Mascope on your machine with Docker (the only prerequisite) over plain HTTP
on `localhost` - no certificates, no build:

```sh
# get docker-compose.release.yaml + .env.example from this repo, then:
cp .env.example .env

# create the secrets
mkdir -p .runtime/secrets
head -c 32 /dev/urandom | xxd -p -c 32 > .runtime/secrets/postgres_password.txt
head -c 32 /dev/urandom | xxd -p -c 32 > .runtime/secrets/jwt_secret_key.txt
head -c 32 /dev/urandom | xxd -p -c 32 > .runtime/secrets/server_owner_secret_key.txt

# pull the published images and start
docker compose -f docker-compose.release.yaml pull
docker compose -f docker-compose.release.yaml up -d
```

Then open <http://localhost:8080>. See
[docs/user/getting-started](docs/user/getting-started/index.md) for loading the
demo dataset, and [docs/ADOPTION_PLAN.md](docs/ADOPTION_PLAN.md) for sharing
Mascope on a LAN.

## Tech stack

| Layer | Technologies |
| --- | --- |
| **Backend** | Python, FastAPI, Uvicorn, Socket.IO, PostgreSQL 16, SQLAlchemy 2 (async), Alembic, Redis, Pydantic |
| **Frontend** | Vue 3, PrimeVue, Vite, served by nginx |
| **SDK** | Python (`mascope_sdk`) for notebooks and scripts |
| **Instrument readers** | OpenTFRaw (open-source Thermo `.raw` reader, default), Tofwerk TOF |
| **Tooling & deploy** | uv workspace, Docker / Docker Compose, GHCR images, the `mascope` CLI |

## Documentation

| For | Where |
| --- | --- |
| **Users** (scientists, operators) | [User docs](docs/user/index.md) (MkDocs site under `docs/user/`) |
| **SDK / notebook users** | [SDK readme](libraries/sdk/README.md) |
| **Developers / contributors** | [Developer guide](docs/dev/developer_guide.md) (build, run, runtime, backend, database, deploy) |
| **Self-hosting & onboarding** | [Adoption plan](docs/ADOPTION_PLAN.md) |
| **Demo dataset & reproducibility** | [Demo dataset](docs/demo_dataset.md) |

## License

[Apache-2.0](LICENSE). See [NOTICE](NOTICE) for attributions.

<!-- TODO: add a citation (Zenodo DOI) once the demo dataset / a release is
archived. -->
