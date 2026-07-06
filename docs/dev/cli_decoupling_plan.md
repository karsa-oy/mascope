# CLI decoupling plan

Goal: publish the Mascope CLI as a standalone PyPI package so an operator can
`pip install mascope-cli` on a fresh machine and use it to install, launch,
update, and back up a Mascope deployment — without a source checkout.

This document records (1) the current entanglement between the CLI and the
application runtime, (2) the phased decoupling plan, and (3) the test strategy
that must land *before* the refactoring starts, so every seam that moves is
covered by a regression net.

## 1. Current entanglement inventory

The CLI lives in `tooling/cli` (package `mascope_cli`, entry point `mascope`).
It is coupled to the monorepo and app runtime in these ways:

### Import-time coupling

- `mascope_cli/runtime.py` instantiates `Runtime("cli")` at module import.
  That constructor:
  - requires the `MASCOPE_PATH` env var (raises otherwise);
  - loads `base.mascope.toml` + `{mode}.mascope.toml` from the repo root and
    an optional env-dir overlay (`.runtime/env/<env>/<mode>.mascope.toml`);
  - creates/reads `.runtime/state.json` (persistent mode/env state);
  - reconfigures the global loguru logger.
  Every command module imports this singleton, so *importing the CLI at all*
  requires a configured monorepo checkout.
- `cmd/prod/main.py` resolves `_COMPOSE_PATH` and `cmd/dev/main.py` resolves
  `DEV_COMPOSE_PATH` from `os.environ["MASCOPE_PATH"]` at import time.
- `cmd/__init__.py` has a load-order hack (demo must import after dev) to
  dodge a circular import through `mascope_cli.pg`.

### Packaging coupling

- `mascope_cli` depends on `mascope_runtime`, which is a uv-workspace-only
  package (not on PyPI). `mascope_runtime` in turn pulls `loguru`, `pydantic`,
  `rich`, and `duckdb` (used only by `logs query`/`logs gc`).
- Undeclared dependencies: `pandas` (demo main/build_bundle/verify) and
  `requests` (demo `_rebuild`) are imported inside functions but absent from
  `tooling/cli/pyproject.toml`. They currently resolve only because the
  monorepo venv installs them via other packages.
- The compose files (`docker-compose.yaml`, `docker-compose.demo.yaml`,
  `docker-compose.dev.yaml`) and the config TOML layers live at the repo
  root, not inside the package — a pip-installed CLI has none of them.

### Checkout-assuming commands

- `mascope test`, `mascope lib`, `mascope dev run` (via `_source_root()`,
  which walks up from the installed package location and falls back to cwd),
  and `mascope dev install`-style flows all assume the monorepo source tree.
- `Runtime.parse_version()` shells out to git in the *current working
  directory* — meaningless outside a checkout (returns "unknown-version").

### Latent bugs to fix during the refactor

- `mascope_runtime/state.py` keeps `state_path` / `temp_state` as **module
  globals**, so all `Runtime` instances in one process share the most
  recently initialized state (e.g. `_compose_env` creating
  `Runtime("frontend", mode="prod")` clobbers the temp-state global).

## 2. Decoupling plan (phased)

### Phase 0 — regression net (this work)

- Hermetic pytest suite for the CLI (`tooling/cli/tests/`): a conftest builds
  a throwaway `MASCOPE_PATH` home from the repo's real TOML layers, so tests
  never touch the developer's `.runtime/state.json` and need no
  pre-configured shell.
- Cover the seams the refactor will move: the entrypoint callback (version
  pinning, log env vars), `parse_version`, `lib.run`, prod compose env
  construction and exit-code propagation, `pg.utils` helpers, and test
  command construction. Whole-tree CliRunner `--help` smoke tests guard the
  fragile import graph.
- CI job that runs the suite on every PR (it currently never runs).

### Phase 1 — kill import-time side effects

- Replace the module-level `runtime` singleton with a lazily initialized
  accessor (e.g. `get_runtime()` memoized, or a Typer context object) so
  `import mascope_cli` is side-effect free.
- Move `_COMPOSE_PATH` / `DEV_COMPOSE_PATH` resolution into the command
  callbacks.
- Untangle the `pg` ↔ `cmd.dev` circular import (move `is_docker_running`
  into a neutral module) and drop the ordering hack in `cmd/__init__.py`.
- Fix the state-global bug while the tests watch.

Behavior is unchanged; this phase is pure mechanics and is where the Phase 0
tests earn their keep.

### Phase 2 — make MASCOPE_PATH optional

- Default `MASCOPE_PATH` to a platform data dir (e.g. `~/.mascope` /
  `%LOCALAPPDATA%\Mascope`) created by a new `mascope init` command; keep the
  env var as an override. The runtime home holds `.runtime/`, secrets,
  filestore, backups — exactly what it holds today, just not inside a git
  checkout.
- Ship the config TOML layers (`base/dev/prod.mascope.toml`) and the prod +
  demo compose files as **package data** inside the wheel; `mascope init`
  materializes them into the runtime home where the operator can override
  them. `parse_version` git fallback is replaced by the installed package
  version (with the git path kept for editable installs).

### Phase 3 — split operator vs developer surface

- Operator commands (published): `init`, `prod up/down/ps/logs/restart`,
  `prod db backup/restore/status`, `cert`, `logs`, `update` (new: pull
  release images + migrate), `demo`.
- Developer commands (monorepo only): `dev *`, `test`, `lib`, `agent`,
  `backend`. Keep them in the package but registered only when a source
  checkout is detected, or split into a `mascope-devtools` extra — decide at
  implementation time; the former is less churn.
- Publish `mascope-runtime` to PyPI (it is already an isolated small
  library), or fold the needed parts (config models, state, logging minus
  duckdb query) into the CLI package. Publishing is preferred — the backend
  shares the code. Make `duckdb` an optional extra either way.
- Declare the real dependency set (`pandas`/`requests` moved to a `demo`
  extra or made lazy-with-error-message), and verify with `deptry`.

### Phase 4 — release automation

- Reuse the existing PyPI trusted-publishing workflow (mascope-sdk /
  mascope-tools precedent) to publish `mascope-cli` on version bump.
- Deployment smoke test (`tooling/smoke-test.sh`) gains a pip-install path:
  install the wheel in a clean venv, `mascope init`, `mascope prod up`
  against release images.

## 3. Test strategy notes

- Unit tests must not require Docker, Postgres, or the network; anything
  that shells out is tested via mocked `lib.run`/`subprocess.run` plus
  argument assertions. Real subprocess use is limited to git (temp repos)
  and `sys.executable`.
- The hermetic conftest is intentionally the same seam Phase 2 formalizes:
  "CLI home directory ≠ source checkout". Tests written against it survive
  the refactor.
- The existing demo tests (`test_demo_deid.py`, `test_demo_verify.py`,
  `test_prod_compose.py`) fold into the same suite unchanged.
- e2e for the packaged CLI (pip install in a container → `mascope init` →
  `prod up`) belongs to Phase 4, not Phase 0.
