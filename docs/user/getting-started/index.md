# Getting started

The fastest way to see Mascope is to run it on your own machine with Docker,
preloaded with the demo dataset. This is a local, single-machine setup served
over `http://localhost` - no certificates, no account signup.

!!! info "Prerequisites"
    [Docker](https://docs.docker.com/get-docker/) (Desktop or Engine) running.
    That is the only requirement for the local trial.

## Run the demo (real data, one command)

Download the demo compose file and start it:

```sh
curl -O https://raw.githubusercontent.com/karsa-oy/mascope/develop/docker-compose.demo.yaml
docker compose -f docker-compose.demo.yaml up
```

It pulls the published images and loads the published demo dataset - a real,
de-identified Orbitrap time series with samples, batches, and matches - before
the app starts. When it is up, open **http://localhost:8080** and log in with:

- **Email:** `demo@mascope.app`
- **Password:** `mascope-demo`

The first run downloads ~150 MB. Tear it down with
`docker compose -f docker-compose.demo.yaml down -v`.

For what is in the bundle (and how it is built and published), see the
[demo dataset guide](../../demo_dataset.md).

## Start with an empty instance

To run a clean Mascope where you register the first owner yourself, use the
release stack instead.

### 1. Get the release files

Download `docker-compose.release.yaml` and `.env.example` from the repository
(or clone it). Copy the example env:

```sh
cp .env.example .env
```

### 2. Create the secrets

```sh
mkdir -p .runtime/secrets
head -c 32 /dev/urandom | xxd -p -c 32 > .runtime/secrets/postgres_password.txt
head -c 32 /dev/urandom | xxd -p -c 32 > .runtime/secrets/jwt_secret_key.txt
head -c 32 /dev/urandom | xxd -p -c 32 > .runtime/secrets/server_owner_secret_key.txt
```

### 3. Pull and start

```sh
docker compose -f docker-compose.release.yaml pull
docker compose -f docker-compose.release.yaml up -d
```

Open **http://localhost:8080** and register the first owner account.

## Next steps

- [Concepts](../concepts/index.md) - the domain model (samples, batches, matching, calibration).
- [Guides](../guides/index.md) - task-by-task how-tos.
- Sharing Mascope with a team on a LAN, or production deployment: see
  [Hosting & deployment](../../hosting.md).
