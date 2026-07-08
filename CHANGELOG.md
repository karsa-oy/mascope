# Changelog

Notable changes to Mascope are documented here. Versions follow the date-based scheme `YYYY.MM.DD-<hash>` produced by the release workflow, and releases are pinned with a semantic version tag `vX.Y.Z`.

## [Unreleased]

### Changed

- `match_isotope` no longer stores non-matching isotopes, cutting the largest
  table in the database by the majority of its rows (on one production instance
  it was 209 GB / 93% of the database, ~80%+ of it placeholder rows). Matching
  scores every candidate isotopologue against the sample peaks, but only those
  that score above zero are a real match; the rest - no peak within the match
  window, or a peak whose m/z error (>= 100 ppm) or abundance error (>= 100%) is
  so large it can never become a match at any read-time tolerance - are now
  dropped on write and **reconstructed on read** from their target isotope. The
  Match-tab isotope table still lists every expected isotope, and all
  higher-level aggregates (`match_ion` / `match_compound` / `match_collection` /
  `match_sample`) are unchanged because a non-matching isotope contributes zero
  to every aggregate. Read-time tolerance loosening is preserved in full: the
  persist threshold coincides exactly with the UI slider ceilings (m/z tolerance
  100 ppm, isotope ratio tolerance 1.0), so every record reachable as a nonzero
  match is still stored. Going forward, matching also writes far fewer rows,
  bounding the growth rate rather than only reclaiming once.
- The Match-tab isotope table shows a match tag only for actual matches
  (possible/probable). Isotopes that are not a match under the current
  tolerances - never detected, or scored zero - now show no tag instead of a
  misleading 0%.

### Added

- `remove_unmatched_match_isotopes` maintenance script (`mascope prod db script
  run remove_unmatched_match_isotopes`) reclaims the historical non-matching
  rows from existing databases. It deletes `match_isotope` rows with
  `match_score = 0` in bounded batches (configurable `BATCH_SIZE`, `DRY_RUN=1`
  to preview) so a multi-hundred-million-row table can be cleaned without one
  giant transaction; the delete is lossless for aggregates. Run `VACUUM FULL
  match_isotope` (or pg_repack) afterwards to return the freed space to the OS.

### Fixed

- `mascope prod db script run` no longer fails with exit 127 on images built
  from source. It resolved the in-container Python from a single hardcoded path
  (`/root/.local/share/uv/tools/...`) that only matched older published images;
  current images install the tool under `/opt/uv/tools`. The runner now probes
  the known tool locations (and falls back to a `python` on `PATH` that can
  import `mascope_backend`), so it works regardless of how the image was built.

## [2026.07.08]

### Added

- Read-path performance benchmark suite (`server/backend/tests/system/benchmark/`, opt-in with `MASCOPE_BENCH_TEST=1`): clones the demo dataset up to thousands of samples and collection ions, then exercises the hot batch-overview and sample-browser endpoints, asserting a per-request latency budget (default 20 s, the frontend timeout) and a response-size budget. A nightly workflow (`.github/workflows/benchmark.yaml`) runs it against a freshly built demo stack and publishes the timings, so a latency or payload-shape regression at scale surfaces before a user hits it.
- Unattended, self-classifying updates for pinned deployments (`mascope-cli`
  2026.7.8). `mascope prod update --check` classifies a pending update as
  up-to-date, a *fast* update (new images, no database migration, near-zero
  downtime) or a *migration* update (a schema migration will run and cause
  downtime) by reading the Alembic head the target release carries and comparing
  it to the live database, so a maintenance window is only scheduled when one is
  actually needed. Releases now publish a small `mascope-manifest.json` (a GitHub
  Release asset) recording that head, which `--check --manifest` reads without
  inspecting the image. `mascope prod update --auto` (driven by the systemd
  `mascope-update.timer` in `tooling/systemd/`) applies fast updates inside a
  configurable maintenance window (`MASCOPE_UPDATE_WINDOW`) with a post-apply
  health check, and applies a migration update once its grace period elapses
  (`MASCOPE_UPDATE_GRACE_DAYS`, default 7) or an operator runs `mascope prod
  update --confirm`; `mascope prod update --snooze N` postpones it. A failed
  health check alerts and stops without rolling back automatically. Release
  discovery uses the public GitHub API over plain HTTPS, so no token is needed.
  `tooling/ubuntu.sh` installs the systemd units (the update timer left disabled
  until you opt in), and `docs/maintaining.md` is the operator runbook covering
  provisioning, updates, backups, and troubleshooting.
- The web UI now survives a full page reload. The active selection chain
  (workspace -> dataset -> batch -> sample -> collection -> ion) is persisted to
  browser storage and restored on load, so a reload - whether from an
  auto-update restarting the backend, a transient network failure, or pressing
  F5 - lands you back where you were instead of near the top of the navigation.

### Changed

- SDK (`mascope-sdk` 2026.7.7): the `load_peaks` / `load_peak_timeseries`
  `batches` and `samples` filters now treat a string as a case-insensitive
  **literal substring** instead of a regex, so values with metacharacters (e.g.
  `"Sample (A)"`) match literally. Pass `exact=True` to match a whole name, or a
  compiled `re.Pattern` (e.g. `re.compile("2025|2026", re.IGNORECASE)`) to filter
  by regex. Callers relying on regex/alternation in a plain string must switch to
  a compiled pattern. The dead `**kwargs` on `MascopeClient.load_peaks` /
  `load_peak_timeseries` was removed, so an unknown keyword such as `batch=...`
  (singular) now raises `TypeError` instead of being silently ignored.

### Fixed

- SDK (`mascope-sdk` 2026.7.7): `POST` requests now send their body as
  `application/json`. Previously the body was serialized with
  `data=json.dumps(...)` and no `Content-Type` header, so the backend received it
  as opaque bytes and rejected every SDK `POST` carrying a body with a 422
  validation error (surfaced by `load_peak_timeseries` on
  `POST /api/samples/{id}/peaks/timeseries`).

## [v1.2.0] - 2026.07.07

### Changed

- The batch overview chart loads its per-sample datapoints through a new columnar endpoint (`POST /api/match/records/ion/series`) that sends each ion's metadata once with parallel per-sample value arrays, scoped by batch ID instead of an explicit list of every sample ID. On a 5,000-sample batch this cuts a full large-collection chart load from minutes of ~25 MB chunk responses to seconds, and the chart no longer rebuilds every Plotly trace from deep clones when toggling the average/sum scale.
- The spectrum, match-spectra and match-timeseries charts no longer deep-clone every Plotly trace when the intensity scale is toggled; they build shallow copies that share the unchanged data arrays. Noticeable on long acquisitions (thousands of scans per trace).
- API responses now carry a `Server-Timing` header and request logs include `duration_ms`, so slow endpoints are visible in browser devtools and server logs without extra tooling.

### Added

- The Mascope CLI is now a standalone PyPI package: `pip install mascope-cli`
  on a machine with Docker, then `mascope init` (creates a runtime home with
  editable config, compose files and generated secrets), `mascope cert gen`
  and `mascope prod up` bring up a deployment — no source checkout needed.
  Importing the CLI is side-effect free, `mascope --help` works before any
  environment exists, and commands without a configured home fail with a
  pointer to `mascope init` instead of a traceback. The standalone install
  ships the operator surface (`init`, `prod`, `env`, `demo`, `logs`, `cert`);
  developer commands (`dev`, `test`, `agent`, `backend`) remain available in
  the monorepo checkout, which is unchanged. The shared runtime library is
  published alongside as `mascope-runtime`. A hermetic CLI test suite and a
  packaging smoke test (wheel installed into an isolated environment) run in
  CI on every PR. Without a `MASCOPE_VERSION` pin, a pip-installed CLI
  deploys the `latest` release images.
- `mascope prod update`: update a deployment in one step — pulls the target
  release images (`--version vX.Y.Z`, or `latest` without a pin), restarts
  the stack with them, and shows container status. Database migrations run
  automatically on startup, preceded by a pre-migration dump; a failed pull
  aborts before the running stack is touched.

- Frontend unit test layer (Vitest): fast, backend-free tests covering formatters, chemistry helpers, batch import validation and API utilities. Run with `npm run test:unit` or `mascope test run frontend`.
- Hermetic end-to-end test suite (Playwright) that runs against the demo stack with API-seeded state, covering login, the app shell, and dataset / batch / target collection management. Both frontend suites now run in CI on every PR, with traces and reports uploaded on failure.
- SDK contract tests: `MascopeClient` is exercised end-to-end against the demo
  stack (workspace resolution, dataset/batch/sample listings, matched peak
  retrieval), doubling as a breaking-change detector for the public REST API.
  They run in CI inside the demo-stack e2e job and locally with
  `MASCOPE_SDK_CONTRACT=1 uv run pytest libraries/sdk/tests/`.
- Upload-to-browse e2e test: a real demo raw file is uploaded through the web
  UI (Uppy/tus), the file-converter runs the real conversion -> peak detection
  -> matching pipeline, and the result must appear in the Raw files browser.
  Unit tests for the converter's building blocks: the peak-detection
  concurrency guard, the upload-context registry whose filename normalization
  decides whether an uploaded file is "registered", and the filestream watcher
  that must queue a file only once it has stopped growing.
- Golden-dataset reproducibility test: the demo bundle's raw files are ingested
  through the real upload -> convert -> match pipeline and the produced peaks
  must reproduce the bundle's golden outputs within the manifest tolerances
  (sub-0.1 ppm m/z). The demo stack gained a rebuild mode
  (`MASCOPE_DEMO_REBUILD=1`) that restores only the reference seed so ingestion
  starts from scratch; CI runs the test nightly and on manual dispatch
  (`.github/workflows/reproducibility.yaml`).
- The `libraries/` test suites (chem, file, match, molmass, signal, thermo, tools)
  now run in CI on every PR; previously they only ran when invoked locally.
- Frontend unit tests for the notification hub (process tracking, badges,
  watcher dispatch, log retention) and the spreadsheet-paste table parser.
- Unit tests for the core matching pipeline: the isotope-to-peak assignment
  rules (closest-in-window, per-ion peak uniqueness, abundance priority, m/z
  ordering) and the match statistics (abundance/mz error and score formulas)
  in `mascope_match`, plus the ion -> compound -> collection/sample aggregation
  rules in the backend match controllers.
- Releases are gated on a smoke test (`tooling/smoke-test.sh`): the demo stack is booted from the freshly built images and must serve the frontend, authenticate the demo login and answer seeded API reads before any image is pushed or tagged `latest`. The script also works against any running deployment.

### Changed

- Documented the test layers in the developer guide and added a repository `CLAUDE.md` runbook for coding agents.
- The matching pipeline is substantially faster: match isotopes are bulk-inserted, aggregation runs once per batch instead of per sample, the row-wise pandas hot paths are vectorized, and candidate peaks are found with binary-search windows instead of dense difference matrices. Behaviour is preserved; the profiled bottleneck (database round-trips and row-wise pandas, ~90% of match time) is what was cut.
- Chemical-formula handling (formula parsing, ion arithmetic, isotope prediction, and the labelled `^N` custom element) is consolidated into `mascope_tools.composition`, and the vendored `mascope_molmass` fork is retired (net -7.2k lines).

### Removed

- The unmaintained instrument-bound Playwright suite. Its batch, dataset and target collection scenarios now live in the hermetic e2e suite; the truly instrument-dependent specs (sample processing, Orbitrap acquisition) were dropped and remain available in git history.
- The vendored `mascope_molmass` fork; its only unique capability (the labelled `^N` custom element) now lives in `mascope_tools.composition`.

### Fixed

- `mascope prod` compose commands (`build`, `up`, ...) now exit with docker
  compose's exit code instead of always reporting success. CI builds release
  images via `mascope prod build` and trusts its exit status, so a swallowed
  build failure previously let jobs continue against stale images.
- Web UI file uploads work again on deployments served from a non-standard
  port (e.g. the demo stack on `:8080`). nginx forwarded `X-Forwarded-Host`
  without the port, the tus upload endpoint built its upload URL from it, and
  every upload chunk was then sent to port 80 and refused. Found by the new
  upload e2e test.
- Frontend linting works again: migrated to the ESLint 9 flat config format (the legacy config had been silently ignored). The revived linter surfaced dormant chart bugs that are now fixed: the batch overview chart's log-scale zoom reset never fired, and two match spectra comparisons were always false.
- The dashboard no longer renders a duplicate `id="app"` element inside the Vue mount point.
- The axios error handlers no longer throw a `TypeError` (masking the real error) when a request fails before a response exists, e.g. a request-setup or network failure; the request/response `config` and body are now guarded before destructuring.

### Security

- API error responses no longer include Python tracebacks, internal filesystem paths, or raw messages of unexpected exceptions (including `AttributeError` and `RuntimeError`, which previously echoed their raw message). Clients receive the user-facing message plus an opaque `error_id`; the full traceback is logged server-side under the same `error_id` for correlation. The same applies to error payloads emitted over Socket.IO notifications.
- Request validation errors no longer echo the raw request body (which can contain credentials) back to the client, and the offending input values are now kept out of the server logs as well (the validation error is logged without its traceback, whose final line rendered the raw input).
- After a batch rematch, an open sample's peak list now refreshes its match/formula annotations. The batch aggregation path emitted only a batch-level event and skipped the per-sample `peak_reload`, so peak annotations went stale until a manual reload.
- The batch overview chart no longer leaks a socket listener on every mount: the match-event handlers are now removed on unmount (they were registered as inline callbacks that `socket.off` could not match by identity).
- Invalid target-compound formulas are now handled safely. Since the replacement parser silently skips characters it does not recognise, a formula that is garbage, a leftover numeric mass, or an unknown custom element previously produced bogus adduct-only ions or an unhandled 500 during isotope prediction; such compounds are now skipped with a warning. The batch match endpoint rejects bare numeric masses like single-compound creation does, and the valid formula `NaN` (sodium nitride) is no longer misclassified as a numeric mass.

## 2026.07.07

### Fixed

- The batch overview no longer times out when loading a large target collection on a large batch (#1584). The batch-level match ion aggregation ranked every match row of every sample in the batch before keeping the best row per ion; it now probes the best in-batch match per requested ion via a new `match_ion (target_ion_id, match_score)` index, so its cost scales with the collection instead of the batch's match volume. Measured on a 5,103-sample batch with a 3,000-ion collection: 13-21 s -> 0.3-1.3 s. Requires a database migration (`alembic upgrade head`).

### Changed

- nginx now serves JSON, JavaScript and CSS responses gzip-compressed (#1585). The batch overview's chart data chunks shrink from ~25 MB to ~1.6 MB on the wire for a 5,000-sample batch; uploads and raw-file downloads are unaffected.

## [v1.1.1] - 2026.07.03

### Fixed

- Runtime now parses release semver tag correctly, enabling to checkout, pull and run a specific release (e.g. `git checkout v1.1.1`, `mascope prod docker pull`, `mascope prod up`)

## [v1.1.0] - 2026.07.03

### Security

- Authentication endpoints (login, first-owner registration, credential change) are now rate-limited per client IP, backed by Redis so limits hold across all workers. This blunts password brute-forcing and credential stuffing.
- New and changed passwords must be at least 12 characters and may not contain the account's email or username. The web UI validates the same policy inline so users get immediate feedback.
- The web session lifetime (auth cookie / JWT) is reduced from 360 days to 7 days, bounding how long a stolen token stays valid.
- The server now warns at startup if the JWT signing secret is shorter than the 32-byte minimum recommended for HS256.
- The backend API is no longer published to a host port. nginx reaches it over the internal Docker network, so the plaintext HTTP API is no longer exposed on a host interface where it could bypass the frontend's TLS termination.
- nginx now sends `Strict-Transport-Security` (HTTPS only), `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy`, and no longer sends a wildcard `Access-Control-Allow-Origin` (the frontend and API share an origin).
- The authentication cookie's `SameSite` policy is set explicitly (`lax`) rather than relying on the library default.

### Fixed

- The file-converter service now connects to the backend over the websocket transport only. With a multi-worker backend it previously failed to establish its Socket.IO session (the polling handshake was load-balanced across workers), resulting in intermittent errors.
- Version tags now use a stable 7-character commit hash, so the image tag a deploy derives matches the one CI published. A full clone previously abbreviated the hash to a longer length than CI's shallow clone, so `mascope prod docker pull` failed with `manifest unknown`.
- Production `docker pull`/`up` now deploy `latest` (or a pinned release / semver tag at HEAD) independent of the checked-out branch, instead of a branch-derived tag that is never published. Local `prod build`/`up --build` still tag and display the current branch's version.

## 2026.07.02

### Added

- Version-pinned releases: a deployment can pin `MASCOPE_VERSION` to a release, and the web UI reports the running version.
- Citation metadata (`CITATION.cff`) and a software DOI for archived releases.
- Community health documents: contributing guide, code of conduct, and security policy.
- SDK example notebooks `06-08`, SDK version `2026.7.2`.

### Changed

- Rewrote the hosting documentation into a step-by-step production deploy and update guide.
- Removed the redundant release compose stack; local trials now use the demo stack.
- Updated backend dependencies, including a `python-socketio` security update.

### Fixed

- Corrected the demo quickstart download URL after the `develop` branch was retired.
- Fixed default values in the instrument parameter test.
- Fixed the Ubuntu installation script `tooling/ubuntu.sh` to work on Ubuntu >= 26.
- Run tests on PR to `master`, make workflow permissions read-only explicitly.

## [v1.0.0] - 2026.06.29

- First public release

[Unreleased]: https://github.com/karsa-oy/mascope/compare/v1.0.0...master
[v1.0.0]: https://github.com/karsa-oy/mascope/releases/tag/v1.0.0
[v1.1.0]: https://github.com/karsa-oy/mascope/releases/tag/v1.1.0
