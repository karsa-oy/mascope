# OpenTFRaw parity harness — migration backrest

Validation for replacing Thermo's `RawFileReader` with the open-source
[OpenTFRaw](https://github.com/Sigilweaver/OpenTFRaw) reader. It quantifies how
closely OpenTFRaw reproduces the numbers the current `mascope_thermo` pipeline
depends on, and — once the gaps are closed — becomes the suite that proves the
app can run on OpenTFRaw alone.

It is **agnostic to which files are present**: point it at a directory and it
discovers every `*.raw` and compares both backends on each one. Drop in more
realistic files later with no code changes.

## How it's structured (read this first)

This is a **backrest**, not just a Phase 0 spike. Two kinds of test:

1. **Real-parity tests** — for everything OpenTFRaw already reproduces. These
   assert agreement within tolerance and **must stay green**; they catch
   regressions as you build the adapter (Phase 1+).
2. **Known-gap tests** — for the capabilities OpenTFRaw 1.1.0 lacks. They assert
   the *target* parity but are marked `xfail`, so they fail today (expected) and
   flip to **`XPASS`** the moment a gap closes (e.g. you land a decoder upstream
   or in a fork). An `xpassed` in the pytest summary is your cue to delete the
   marker and keep the assertion as a permanent guard.

**End state:** every gap closed → no `xfail` remaining → the suite passes
outright. That is the same condition under which `mascope_thermo` can drop the
Thermo backend. The suite is the checklist.

## Requirements

Run on a machine / venv that has **both** backends:

- `mascope_thermo` (this repo) — pulls in `pythonnet` + the bundled .NET DLLs.
  Needs the .NET runtime (Windows, or Linux/macOS with a working CoreCLR).
- `opentfraw` — a runtime dependency of `mascope_thermo` (installed by `uv sync`).

Run **from the repository root** so the Thermo DLL loader resolves its relative
path (`./libraries/thermo/src/mascope_thermo/lib/dlls/`).

## Run it

As tests (via the project CLI, or pytest directly):

```bash
uv run mascope test run libraries -m thermo
# direct, with the per-file numeric report (-s) and xfail/xpass reasons (-rxX):
uv run pytest libraries/thermo/tests/test_parity.py -v -s -rxX
```

As a script (prints a markdown report, optionally writes JSON + markdown). Run
the file directly — the `parity` package isn't importable as `-m` from the root:

```bash
# default: the bundled libraries/thermo/tests/test_files/
uv run python libraries/thermo/tests/parity/parity.py

# your own folder of realistic files, with saved artifacts
uv run python libraries/thermo/tests/parity/parity.py /path/to/raw_files \
    --json parity.json --md parity_report.md
```

The script exits non-zero if any file's heuristic verdict is not `PASS` (handy
for CI); the precursor gap alone makes MS² files `WARN`.

Environment overrides:

| Variable | Meaning |
| --- | --- |
| `MASCOPE_PARITY_RAW_DIR` | directory of `.raw` files to compare |
| `MASCOPE_PARITY_MIN_MATCH` | min acceptable median centroid-match fraction (default 0.99) |

If a backend is missing or no `.raw` files are found, the tests **skip** rather
than fail.

## What it checks

Per scan, aligned 1:1 by scan number:

- scan count, retention time (min), polarity, MS level
- TIC, base-peak m/z + intensity
- filter-string exact-match rate (formatting may legitimately differ)
- centroid peaks: matched fraction within a ppm window, and the m/z (ppm) and
  intensity (relative) deviation of matched peaks
- **MS² metadata:** precursor m/z (gap), isolation width, HCD energy (nominal)
- injection time, charge state
- instrument model (best-effort containment match)

## Known gaps (currently `xfail`)

Confirmed from the OpenTFRaw Python binding and the assessment (Section 5):

1. **No per-peak resolution / S:N / noise** — centroid is `{mz, intensity}` only.
   Instrument-config (resolution-function) fitting depends on it.
   → `test_resolution_parity`
2. **No MS² precursor m/z** — returned as `None`, and stripped from the filter
   string, so `_group_ms2_scans_by_parent` can't be reproduced as-is.
   → `test_ms2_precursor_parity`
3. **No profile / SegmentedScan arrays** in Python (centroids + mzML export
   only). `get_signal` / `compute_sum_signal` read profile data.
   → `test_profile_parity`

Two more gaps are **not** in this harness because OpenTFRaw has no equivalent to
compare against — they are reimplemented in numpy during Phase 2 and need their
own tests against the Thermo reference:

- multi-scan ppm averaging (`Extensions.AverageScans`, assessment §5.3)
- arbitrary-m/z XIC (`GetChromatogramData`, assessment §5.4)

Also note: OpenTFRaw's `collision_energy` is the *nominal* HCD value (the `@hcd`
in the filter), not the calibrated `"HCD Energy V:"` trailer that
`get_ms2_summary_metadata` currently reads — decide which the port should use.
