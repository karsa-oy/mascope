# Demo dataset & end-to-end reproducibility

Status: `mascope demo` (create/load/update + seeding + two-dump bundle), the
golden export, and the keyed reproducibility comparison are implemented; the
**v1.0.0** demo bundle is published to Zenodo. Remaining: driving the heavy
full-stack reproducibility test in CI. Last revised June 2026.

This document describes how Mascope ships a public **demo dataset** so that a
newcomer can install Mascope and immediately have real data to explore, and how
the same artifact powers an **end-to-end reproducibility test**.

The two goals are deliberately served by one artifact: the raw instrument files
are the single source of truth, and everything else (an instant-load database
snapshot, the golden outputs the reproducibility test compares against) is
*derived* from them by a documented, repeatable build step.

## Contents

- [Goals](#goals)
- [The demo bundle](#the-demo-bundle)
- [Where it lives](#where-it-lives-hosting)
- [The `mascope demo` command](#the-mascope-demo-command)
- [End-to-end reproducibility test](#end-to-end-reproducibility-test)
- [De-identification](#de-identification)
- [Step-by-step: create, load, and update](#step-by-step-create-load-and-update)
  - [A. Create a new demo dataset](#a-create-a-new-demo-dataset-from-raw-files)
  - [B. Load the demo (newcomer)](#b-load-the-demo-newcomer)
  - [C. Update an existing demo dataset](#c-update-an-existing-demo-dataset)
  - [D. Publish to Zenodo (versioning)](#d-publish-to-zenodo-versioning)
- [Lowering the adoption threshold](#lowering-the-adoption-threshold-beyond-data)
- [Open questions](#open-questions)

## Goals

1. **Lowest possible adoption threshold.** A newcomer should get from "cloned the
   repo" to "looking at real data in the Mascope UI" in one command, with Docker
   as the only hard prerequisite. The primary entry point is a one-command local
   demo: `mascope demo`.
2. **End-to-end reproducibility.** Anyone can re-run the full ingestion + matching
   pipeline on the published raw files and confirm they reproduce the published
   results within documented tolerances. This doubles as a regression gate in CI.

A hosted public demo instance (zero-install browsing) is a natural later layer -
it is simply `mascope demo` running on a server we own - but it is out of scope
for the first iteration.

## The demo bundle

The canonical artifact is a single versioned **demo bundle**. Its raw files are
the source of truth; the snapshot and expected outputs are generated from them.

```
mascope-demo-dataset-v1/
  raw/             # de-identified Thermo .raw files - the SOURCE OF TRUTH
  seed/            # AUTHORED: pg_dump of reference data (ionization modes,
                   #   instrument config, calibration/diagnostic collections,
                   #   demo user) - restored by --rebuild BEFORE ingesting raw
  snapshot/        # DERIVED: pg_dump (.dump) + filestore tree (the "instant" path)
  expected/        # DERIVED: golden outputs (parquet) the reproducibility test asserts
  manifest.json    # names, instrument, ionization, sha256s, versions, tolerances
  DATA_LICENSE     # data license (e.g. CC-BY-4.0) - separate from the code license
  README.md        # human-facing description of the measurement
```

The split matters: the **seed** is *authored* reference data the pipeline needs
to exist before it can calibrate + match (it cannot be derived from the raw
files), while **snapshot**/**expected** are *derived* by running the pipeline.
A from-scratch rebuild restores the frozen seed, then regenerates everything
else from the raw files — so the authored reference data is reproducible (a
checksummed fixture) without hand-coding ionization modes and collections.

The first dataset is a ~90-minute alternating positive/negative-mode Orbitrap
time series acquired 2025-08-11 (source instrument `KORBI2`, published under the
alias `Orbion`): 161 `.raw` files (~70 MB total), positive-mode urea (`Ur`) and
negative-mode bromide (`Br`) standards. It
exercises batching, both polarities, intra-sample timeseries, and matching - a
genuinely representative slice of what Mascope is for.

### `manifest.json`

The manifest makes a bundle self-describing and lets `mascope demo` and the
reproducibility test verify exactly what they loaded. Shape:

```jsonc
{
  "bundle_version": "v1",
  "created": "2026-06-23T00:00:00Z",
  "measurement": {
    "instrument": "KORBI2",
    "instrument_type": "orbi",
    "acquired": "2025-08-11",
    "description": "Alternating pos (urea) / neg (bromide) standards time series"
  },
  "produced_with": {
    "mascope_version": "<git describe at snapshot time>",
    "schema_revision": "<alembic head>",
    "opentfraw_version": "<pinned reader version>"
  },
  "raw": [
    { "name": "Orbion_pos_Ur...raw", "sha256": "...", "bytes": 531701 }
    // ... one entry per raw file
  ],
  "seed": { "dump": "seed/mascope_demo.dump", "sha256": "..." },
  "snapshot": { "dump": "snapshot/mascope_demo.dump", "sha256": "...", "filestore": "snapshot/filestore" },
  "expected": { "peaks": "expected/peaks.parquet", "sha256": "..." },
  "tolerances": { "mz_ppm": 0.1, "intensity_rel": 0.01, "area_rel": 0.02 }
}
```

`produced_with.opentfraw_version` is load-bearing: the reproducibility test pins
it so that a reader change which shifts the numbers is caught (see
[OpenTFRaw migration](../libraries/thermo/OpenTFRaw_migration.md)).

## Where it lives (hosting)

The bundle is published to **Zenodo**, which gives a citable DOI and - crucially -
**immutable** versions. Immutability is exactly what a golden-snapshot
reproducibility test needs: the bytes are frozen, so the test can assert a
SHA-256 and trust it indefinitely. Zenodo also handles the ~70 MB (and headroom
to ~50 GB) for free, and the dataset changes rarely, so ongoing maintenance is
near-zero - upload once per bundle version and never touch it again.

The permanent download URL is recorded in the bundle registry (see
`tooling/cli/src/mascope_cli/cmd/demo/bundles.py`) and consumed by
`mascope demo fetch`. The DOI is referenced from the top-level README.

GitHub Releases were considered but rejected as the canonical home: release
assets are mutable and conventionally re-cut per code release, which is *more*
churn for a dataset that should be frozen, and they carry no citation.

## The `mascope demo` command

A new top-level CLI app (`tooling/cli/src/mascope_cli/cmd/demo/`). It always
operates on a dedicated `demo` runtime env in `dev` mode so it never touches a
developer's working env.

```sh
mascope demo                 # fetch (if needed) -> seed -> launch the app on the demo env
mascope demo --fresh         # clean empty env (no bundle) for authoring reference data
mascope demo --rebuild       # ingest from raw through the real pipeline instead of restoring
mascope demo --local <dir>   # use a local bundle dir instead of fetching (pre-publish testing)
mascope demo --no-launch     # seed only, don't start the app
mascope demo fetch           # download + checksum-verify the bundle into the local cache
mascope demo verify          # run the reproducibility comparison against expected/ goldens
mascope demo snapshot        # MAINTAINER: regenerate snapshot/ + expected/ from raw/
```

### Seed path (default) - the "instant" experience

1. Force env `demo`, mode `dev` by setting `MASCOPE_ENV=demo` in the process
   environment. The runtime checks `MASCOPE_ENV` first when resolving the active
   env, so the whole process and every launched subprocess use `demo` without
   any `mascope env use demo` step.
2. Create the dev secrets the backend reads if they do not exist
   (`postgres_password.txt`, `jwt_secret_key.txt`, `server_owner_secret_key.txt`
   — the SSL cert is prod-only), so a newcomer needs no manual secret setup;
   check Docker; start PostgreSQL + Redis (`mascope dev up` plumbing); wait ready.
3. Create the `demo` env dir and its standard subdirs (`filestore`,
   `filestreams`, `temp`, `logs`, `agents`) if missing; create the
   `mascope_demo` database.
4. `fetch`: download the bundle from Zenodo into the cache, verify every
   `raw`/`snapshot` SHA-256 against the manifest.
5. Restore `snapshot/mascope_demo.dump` into `mascope_demo` (reusing the
   `pg_restore` path from `mascope dev db restore`) and copy the filestore tree
   into the demo env's `filestore/`.
6. Launch `backend`, `frontend`, `file-converter` (reusing `dev run`'s
   `_run_application`).
7. Seed fixed demo credentials (below) and print the local URL, login, and SDK
   token.

The seeded demo user + token are the real unlock for a low threshold: they
remove the owner-registration and token-generation steps before a first look,
and make the SDK (`pip install mascope_sdk`) work against the local demo out of
the box.

### Demo credentials

Fixed and well-known, seeded after the database is ready by
`mascope_backend/db/scripts/seed_demo.py` (also runnable standalone via
`mascope dev db script run seed_demo`). The seed is idempotent — it resets the
password every run and re-creates the SDK token with a fresh timestamp, so the
credentials work regardless of how old a restored snapshot is.

| What       | Value                                  |
| ---------- | -------------------------------------- |
| Web login  | `demo@mascope.app` / `mascope-demo`    |
| SDK token  | `mascope_demo_sdk_token`               |
| Role       | `owner`, superuser                     |

The seed also creates `file-converter` and `file-agent` service tokens for the
demo user: the upload route fetches the `file-converter` token internally to hand
to the converter, and the rebuild upload uses the `file-agent` token as its
bearer (matching the File Agent). All have fresh timestamps each seed run.

The demo user is an **owner**, which also satisfies the app's "first owner"
registration gate (the UI shows a first-owner signup page until an owner-role
user exists) — so the seeded account replaces that signup step entirely. As a
superuser it also bypasses workspace-membership checks and sees all demo data
with no extra wiring. These credentials are **public and for local demo use
only** — the seed script must never run against a real deployment.

Because access tokens expire (`created_at` + lifetime), the token is **not**
baked into the snapshot; it is (re)created by the seed step at demo time so it is
always fresh. The seed runs on both the snapshot and `--rebuild` paths.

### Rebuild path (`--rebuild`) - the "reproducibility" experience

Identical to the seed path through step 3, then instead of restoring the full
snapshot:

4. Restore the **reference seed** (`seed/mascope_demo.dump`) so the pipeline has
   the ionization modes, instrument config, and calibration/diagnostic
   collections it needs to calibrate + match. If the bundle has no seed, the
   rebuild falls back to an empty DB and processing skips calibration/matching
   (with a warning).
5. Launch the app (`backend`, `frontend`, `file-converter`). A background thread
   waits for the backend HTTP server, then uploads each `raw/` file to the real
   `POST /api/sample/files/upload` endpoint (via `mascope_sdk.api_post_file`,
   replicating the File Agent's request: bearer `file-agent` token +
   `X-Service-Name: file-agent`).
6. The endpoint registers the file context (auth) and writes each file to
   `filestreams/`; the `file-converter` ingests them and runs the pipeline,
   using the seeded reference data to calibrate + match.

Direct file drops into `filestreams/` cannot work: the file context (uploader
identity + access token) is registered *only* by the upload endpoint, so a
dropped file is "not registered" and fails. Going through the endpoint is what
gives the converter its auth context — the same path the File Agent uses.

This path runs the *real* `RawProcessor` -> peak detection -> matching pipeline,
so it is what the reproducibility test drives.

## End-to-end reproducibility test

Location: `server/backend/tests/system/reproducibility/`.

The test is the asserted form of the `--rebuild` path:

1. Spin up a clean throwaway DB/env (system-test harness).
2. Assert input integrity: every `raw/` file SHA-256 matches the manifest.
3. Run the real conversion + peak detection + matching pipeline on `raw/`.
4. Export the produced peaks and compare against `expected/peaks.parquet`. The
   goldens are the **found** isotope peaks (`match_score > 0`); matching scores
   every possible isotopologue but the vast majority have negligible abundance
   and are never detected (scored 0). Each peak is joined on the **stable key**
   `(filename, target_isotope_id)` - both survive a rebuild, unlike
   `sample_item_id`, which is regenerated every ingestion - and asserted within
   the manifest's tolerances:
   - every golden peak has a produced peak with the same key,
   - m/z within `mz_ppm`, intensity within `intensity_rel`,
   - no unexpected extra peaks.
5. Pin `opentfraw` to `produced_with.opentfraw_version`; a mismatch fails loudly.

The export seam is `mascope_backend.db.scripts.export_goldens.get_golden_peaks`
(a plain ORM read, so the backend stays free of pandas); the CLI
(`build_bundle.export_goldens`) writes it to `expected/peaks.parquet`. The
comparison logic is shared with `mascope demo verify` (one implementation in
`tooling/cli/src/mascope_cli/cmd/demo/verify.py`, unit-tested in
`tooling/cli/tests/test_demo_verify.py`) so the CLI and the test never drift.

Because the key includes `filename`, the goldens must be captured from a
from-bundle rebuild (step A4 below) so the stored filenames match what a
reproducibility rebuild of the same `raw/` produces.

Because it boots the stack and ingests 166 files, this is a **heavy** test -
tagged so it runs on a schedule / pre-release rather than on every commit.

When the pipeline legitimately changes the numbers, regenerate the goldens
deliberately with `mascope demo snapshot --update`, review the diff, and cut a
new bundle version (see below). The goldens are never updated silently.

## De-identification

The chosen data is a **real, de-identified** measurement. The published bundle
must not leak anything sensitive. The build step
(`tooling/cli/src/mascope_cli/cmd/demo/build_bundle.py`, invoked via
`mascope demo snapshot`) produces a de-identification **report**
(`deid_report.md`) of everything it can read from the files and filenames so a
human can sign off. Candidate identifiers in this dataset:

- **Filenames** embed the instrument label, a redundant human-readable
  timestamp, a run index, the sample short-names (`Ur`, `Br`), and a compact
  acquisition stamp. The instrument label is aliased and the redundant timestamp
  and run index are stripped by the rename step below; the sample short-names are
  standards (kept), and the compact stamp is kept so the timeseries stays
  meaningful.
- **Embedded `.raw` metadata** may include operator name, sample comments, and
  instrument serial. The build report surfaces these; the maintainer decides
  what (if anything) needs scrubbing before publishing.

Deep rewriting of Thermo `.raw` binary internals is intentionally avoided unless
the report flags something genuinely sensitive - it is risky and, for standards
runs, generally unnecessary. The final "is this publishable" call rests with the
data owner, not the tooling.

### Filename de-identification

The build renames every raw file to strip identifiers while keeping byte content
(and therefore checksums) unchanged:

```
KORBI2_2025.08.11-14h23m12s_pos_Ur_NoRI_1_20250811142302.raw
  -> Orbion_pos_Ur_NoRI_20250811142302.raw
```

- the instrument label is aliased (`KORBI2` -> `Orbion`, see `INSTRUMENT_ALIASES`),
- the redundant human-readable timestamp (`2025.08.11-14h23m12s`) is removed,
- the run index (the `_1_` segment) is removed,
- polarity, sample short-name, RI marker, and the compact acquisition stamp are kept.

The published `manifest.json` records only the de-identified names and never the
original instrument label. The de-identification report lists the full original
-> published rename map for sign-off, so it contains the real instrument label
and **must never be published**. The builder therefore writes it as a *sibling*
of the bundle directory — `<BUNDLE>.deid_report.md`, never inside `<BUNDLE>/` —
so it cannot be swept into the archive by accident.

## Step-by-step: create, load, and update

This is the practical how-to. All commands are run from the repo root with the
Mascope venv active (or prefixed with `uv run`). Docker must be running.

Throughout, `<RAW>` is the directory of de-identified raw files (the source of
truth, kept outside the repo) and `<BUNDLE>` is the working bundle directory the
tooling builds and accumulates into (e.g. `mascope-demo-dataset-v1/`).

### A. Create a new demo dataset (from raw files)

1. **Prepare + de-identify the raw files.** Collect the `.raw` files into `<RAW>`.
   The build renames them on copy (instrument aliased, redundant timestamp + run
   index stripped); see [De-identification](#de-identification). Confirm the
   `<BUNDLE>.deid_report.md` sign-off report (written in step 3) before
   publishing.

2. **Author the reference data.** Bring up a clean, empty demo env (no bundle):

   ```sh
   mascope demo --fresh            # offers to reset mascope_demo; say yes
   ```

   Log into the UI at `http://localhost:8090` as `demo@mascope.app` /
   `mascope-demo` and create everything the pipeline needs *before* it can
   process raw: ionization modes/mechanisms, the instrument config, and the
   calibration + diagnostic target collections. Do **not** ingest raw files yet.

3. **Capture the reference seed:**

   ```sh
   mascope demo snapshot --raw <RAW> --out <BUNDLE> --seed
   ```

   This copies `raw/`, writes `manifest.json`, exports `seed/mascope_demo.dump`
   (the authored reference data), and writes the `<BUNDLE>.deid_report.md`
   sign-off report as a sibling of `<BUNDLE>`. Stop the running demo (Ctrl+C)
   before the next step so the database can be reset.

4. **Rebuild from the seed** (restores the seed, then ingests raw through the
   real upload endpoint and runs the pipeline):

   ```sh
   mascope demo --rebuild --local <BUNDLE>
   ```

   Watch the logs for `Uploading N raw file(s)` and the converter ingesting them.
   In the UI, confirm calibration looks right and run/confirm matching against
   the target collection.

5. **Capture the full snapshot + goldens:**

   ```sh
   mascope demo snapshot --out <BUNDLE> --update
   ```

   `--raw` is omitted here: step 3 already copied the raw files into `<BUNDLE>`,
   so the refresh reuses them (no re-copy/re-hash). This exports `snapshot/`
   (pg_dump + filestore) and `expected/` goldens, and preserves the `seed/`
   block already in the manifest. `<BUNDLE>` now holds
   `raw/ + seed/ + snapshot/ + expected/ + manifest.json`.

6. **Publish** to Zenodo and register the bundle — see
   [D. Publish to Zenodo](#d-publish-to-zenodo-versioning).

### B. Load the demo (newcomer)

Once a bundle is published and registered in `bundles.py`:

```sh
mascope demo            # instant: fetch bundle -> restore snapshot -> launch
```

To exercise the full pipeline from raw instead of the instant snapshot:

```sh
mascope demo --rebuild  # fetch -> restore seed -> upload raw -> launch
```

Both seed the fixed demo credentials and print the URL + login + SDK token.
`mascope demo fetch` downloads + checksum-verifies without launching;
`mascope demo info` shows the registered/cached status.

### C. Update an existing demo dataset

- **Re-author reference data** (new ionization mode, different calibration
  collection): repeat A2-A3 to refresh `seed/`, then A4-A5 to regenerate
  `snapshot/` + goldens.
- **Pipeline changed the numbers** (a reader/algorithm change you accept):
  re-run A4-A5 to regenerate `snapshot/` + `expected/`, **review the golden
  diff vs the previous bundle**, and pin the new `opentfraw` version. Goldens
  are never updated silently.
- **Add/replace raw files**: update `<RAW>`, then re-run from A3.

Either way, publish as a **new Zenodo version** (D) and bump the registry.

### D. Publish to Zenodo (versioning)

The published artifact is a single archive of the `<BUNDLE>` directory. The
sign-off report lives *outside* `<BUNDLE>` (as `<BUNDLE>.deid_report.md`), so a
plain archive of the directory contains nothing sensitive - no excludes needed.

1. **Package** the bundle (zip the whole `<BUNDLE>` directory):

   ```sh
   # POSIX
   cd <BUNDLE> && zip -r ../mascope-demo-v1.zip . && cd -
   ```

   ```powershell
   # Windows PowerShell
   Compress-Archive -Path <BUNDLE>\* -DestinationPath ..\mascope-demo-v1.zip -Force
   ```

2. **Upload to Zenodo:**
   - *First release:* create a new Zenodo upload, attach the zip, fill in
     authors/description/license (e.g. CC-BY-4.0), and publish. Zenodo mints a
     **concept DOI** (always points at the latest version) and a **version DOI**
     (this exact version).
   - *Subsequent releases:* open the existing record -> **New version** -> replace
     the file -> publish. This keeps the concept DOI and mints a fresh version
     DOI. Never edit a published version's files in place - immutability is the
     point.

3. **Get the permanent file URL** from the published version (the direct
   `.../records/<id>/files/mascope-demo-v1.zip` link) and the archive **MD5** -
   Zenodo displays the MD5 fingerprint next to the file, so just copy it (no
   local hashing needed). The strong per-file integrity check uses the SHA-256s
   already recorded in `manifest.json`.

4. **Register** the version in
   [`tooling/cli/src/mascope_cli/cmd/demo/bundles.py`](../tooling/cli/src/mascope_cli/cmd/demo/bundles.py):

   ```python
   BUNDLES = {
       "1.0.0": Bundle(
           version="1.0.0",
           url="https://zenodo.org/records/<id>/files/mascope-demo-dataset-v1.zip",
           archive_md5="<MD5 shown by Zenodo>",
           doi="10.5281/zenodo.<version-id>",
       ),
   }
   DEFAULT_BUNDLE_VERSION = "1.0.0"
   ```

   Use a semver version string (Zenodo recommends it): bump PATCH when a
   pipeline/scoring change regenerates the goldens, MINOR when samples or
   reference collections are added, MAJOR when the underlying data changes. Add a
   new key (e.g. `"1.1.0"`) for each new version and bump
   `DEFAULT_BUNDLE_VERSION`; keep old entries so pinned reproducibility runs stay
   resolvable. Reference the **concept DOI** in the top-level README.

5. **Verify** the published bundle end to end:

   ```sh
   mascope demo fetch --force      # downloads + checksum-verifies
   mascope demo                    # instant load from the published snapshot
   ```

## Lowering the adoption threshold (beyond data)

Two cheap, high-leverage wins that compound with the demo command:

- **Publish prebuilt images to GHCR** so `mascope prod up` and the demo *pull*
  `ghcr.io/karsa-oy/mascope-*` instead of building from source - removing the
  longest, most failure-prone part of first run.
- **Keep Docker the only hard prerequisite** for "just try it." This is already
  true now that the default OpenTFRaw reader dropped the Thermo/.NET dependency;
  the README should say so prominently.

## Open questions

- **Demo target collection.** Which target compounds/collection ships seeded so
  matching produces something interesting out of the box? (Needs the data
  owner's input - likely urea + bromide + common contaminants.)
- **Subset for CI.** The full 161-file rebuild is heavy. Do we ship a smaller
  N-file subset bundle for a fast CI reproducibility check, with the full bundle
  reserved for scheduled runs? (The cost is the rebuild + ingestion, not the
  comparison: the golden set is ~42k found peaks and the keyed compare runs in a
  fraction of a second.)
