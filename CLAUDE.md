# Mascope — agent guide

Mascope is a mass-spectrometry analysis web app: FastAPI backend (`server/backend`),
Vue 3 + PrimeVue frontend (`server/frontend`), shared Python libraries (`libraries/`),
Typer CLI (`tooling/cli`, entry point `mascope`). Postgres + Redis run via docker
compose. See `docs/dev/developer_guide.md` for the full picture.

## Running tests

| Suite | Command | Needs | Speed |
|---|---|---|---|
| Backend (pytest) | `mascope test run` or `uv run pytest server/backend/tests/` | Postgres (`mascope dev up`) | minutes |
| Libraries (pytest) | `mascope test run libraries` | nothing | fast |
| Frontend unit (Vitest) | `npm run test:unit` in `server/frontend` | nothing | ~1 s |
| Frontend e2e (Playwright) | `npm run test:e2e` in `server/frontend` | a running stack, see below | minutes |
| Deployment smoke | `bash tooling/smoke-test.sh` | a running stack | seconds |

Run the suite that covers what you changed before finishing. Frontend unit tests are
the default place for new frontend tests; only reach for e2e when the behavior spans
the real backend.

### The e2e stack

The hermetic e2e suite (`server/frontend/tests/e2e/`) targets the demo stack:

```sh
docker compose -f docker-compose.demo.yaml up -d   # frontend at http://localhost:8080
```

It comes preloaded with the published demo dataset and login `demo@mascope.app` /
`mascope-demo` (first start downloads ~150 MB). Point the suite elsewhere with
`MASCOPE_E2E_BASE_URL` / `MASCOPE_E2E_API_URL` / `MASCOPE_E2E_EMAIL` /
`MASCOPE_E2E_PASSWORD`. The upload spec needs a demo raw file
(`MASCOPE_E2E_RAW_FILE`; defaults to the local bundle cache under
`.runtime/demo/`, skips if none found).

### Writing and debugging tests

- Auth is handled once in `tests/e2e/setup/auth.setup.js` (API login → storage state).
  Seed further state through the `api` and `scratch` fixtures in
  `tests/e2e/fixtures/index.js`, not by clicking through the UI. The `scratch`
  fixture provides a per-test workspace + dataset and cleans up after itself.
- Prefer `getByLabel` / `getByRole` locators; add `data-testid` only where no
  accessible handle exists.
- e2e runs keep a trace on failure: `npx playwright show-trace test-results/<...>/trace.zip`.
  Debug a single test with `npm run test:only -- "<name>"` or `test:headed` / `test:trace`.
- Unit tests live in `server/frontend/tests/unit/`, mirroring `src/` paths
  (`tests/unit/lib/chem.spec.js` covers `src/lib/chem.js`).

## Conventions

- Conventional Commits (`type(scope): description`); ASCII-only commit messages,
  no Co-Authored-By trailers.
- CI (`.github/workflows/tests.yaml`) runs backend pytest, frontend unit, and the
  demo-stack e2e suite on every PR; releases are gated on `tooling/smoke-test.sh`.
