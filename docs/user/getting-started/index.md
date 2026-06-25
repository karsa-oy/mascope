# Getting started

The fastest way to see Mascope is to run it on your own machine with Docker and
load the demo dataset. This is a local, single-machine setup served over
`http://localhost` - no certificates, no account signup.

!!! info "Prerequisites"
    [Docker](https://docs.docker.com/get-docker/) (Desktop or Engine) running.
    That is the only requirement for the local trial.

## 1. Get the release files

Download `docker-compose.release.yaml` and `.env.example` from the repository
(or clone it). Copy the example env:

```sh
cp .env.example .env
```

## 2. Create the secrets

```sh
mkdir -p .runtime/secrets
head -c 32 /dev/urandom | xxd -p -c 32 > .runtime/secrets/postgres_password.txt
head -c 32 /dev/urandom | xxd -p -c 32 > .runtime/secrets/jwt_secret_key.txt
head -c 32 /dev/urandom | xxd -p -c 32 > .runtime/secrets/server_owner_secret_key.txt
```

## 3. Pull and start

```sh
docker compose -f docker-compose.release.yaml pull
docker compose -f docker-compose.release.yaml up -d
```

Open **http://localhost:8080** and register the first owner account, or load the
demo data (see below) which seeds a ready-to-use account.

## 4. Load the demo dataset

<!-- TODO: finalize once the demo bundle is published (Zenodo) and the
container-mode `mascope demo` lands. For now, link to docs/demo_dataset.md. -->

The demo dataset (a real, de-identified Orbitrap time series) lets you explore a
populated instance immediately. See the demo dataset guide for how to load it.

## Next steps

- [Concepts](../concepts/index.md) - the domain model (samples, batches, matching, calibration).
- [Guides](../guides/index.md) - task-by-task how-tos.
- Sharing Mascope with a team on a LAN, or production deployment: see
  [Hosting & deployment](../../hosting.md).

<!-- TODO Phase 1: replace the manual download/secret steps with a one-liner
once the standalone CLI or a bootstrap script exists. -->
