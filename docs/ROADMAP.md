# Mascope roadmap

Near-term direction for making Mascope easy to **try, adopt, self-host, and
learn**. A living document - a PR that completes an item should update it.

## Decisions

Settled, so they need not be re-litigated.

- **Documentation tooling:** MkDocs + the Material theme, organised by the
  [Diataxis](https://diataxis.fr/) split under `docs/user/`. The built site is
  bundled into the frontend image and served by nginx at `/docs/`, so the docs
  version always matches the deployed app and in-app help can deep-link to it.
- **Hosting model:** offered both as **managed hosting by Karsa** and as
  **self-hosting**. Local trials run over plain HTTP on `localhost` (the release
  stack); networked/production deployments run over HTTPS. See
  [Hosting & deployment](hosting.md).
- **Demo dataset:** one versioned bundle with de-identified raw files as the
  source of truth, a reference *seed* dump plus a full *snapshot*, published on
  Zenodo with a citable DOI, and loaded via `mascope demo`. See
  [Demo dataset](demo_dataset.md).
- **Approachability fixes shipped:** one-command local HTTP release stack
  (pull-and-run GHCR images), plus the cold-start fixes (role seeding, frontend
  origin/protocol, TLS cert hardening, release-stack isolation).

## In progress / planned

### Demo dataset & reproducibility

- Author the reference data (ionization modes, instrument config,
  calibration/diagnostic collections), capture the seed + snapshot, publish the
  bundle to Zenodo, and register its URL/DOI in the bundle registry.
- Wire `export_goldens` and enable the end-to-end reproducibility test.
- Container-mode `mascope demo` so the demo loads onto the published images.

### Onboarding & hosting

- One-command load of the published demo bundle onto a running stack.
- Standalone CLI on PyPI (`pipx install mascope` -> `mascope demo`).
- Self-hosting niceties: documented mkcert / reverse-proxy (Let's Encrypt) TLS
  paths for warning-free LAN access.

### Documentation

- Build out the user docs: core analysis workflows, operators + SDK, and a
  reference section (glossary, FAQ, troubleshooting).
- Serve the built docs at `/docs/` from the frontend nginx; add
  `mkdocs build --strict` to CI (first reconcile cross-directory and source-code
  links, e.g. `hosting.md` and the `how-it-works` source pointers, to absolute
  URLs).
- Consolidate in-app help: keep popovers to a short hint and move longer
  explanations into the docs, linked via the popover `doc` field (mechanism
  already in place) - a single source of truth.
- README polish: light/dark screenshot via `<picture>`; add a citation once a
  Zenodo DOI exists.
