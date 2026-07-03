# Changelog

Notable changes to Mascope are documented here. Versions follow the date-based scheme `YYYY.MM.DD-<hash>` produced by the release workflow, and releases are pinned with a semantic version tag `vX.Y.Z`.

## [Unreleased]

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
