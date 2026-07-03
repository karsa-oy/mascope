# Changelog

Notable changes to Mascope are documented here. Versions follow the date-based scheme `YYYY.MM.DD-<hash>` produced by the release workflow, and releases are pinned with a semantic version tag `vX.Y.Z`.

## [Unreleased]

### Fixed

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
