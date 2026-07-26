# Import data files

Getting a measurement into Mascope is a two-step process: **upload** the raw
instrument file, then **process** it into one or more samples inside a batch.
Raw files can reach Mascope two ways — automatically via the **File Agent**
running on the instrument PC, or by **uploading from your computer** in the web
app. Either way, you process them the same way afterwards.

New to the terms *sample file*, *sample*, *batch*, and *ionization mode*? See
[Concepts](../concepts/index.md) first — this guide assumes them.

## Prerequisites

Before your first import, make sure the following are in place.

**Your access.** An **editor** role (or higher) in the instrument's workspace.
Guests can view and export but cannot upload or process. See
[Authorization](https://github.com/karsa-oy/mascope/blob/master/docs/authorization.md).
Uploading a file for a brand-new instrument creates that instrument's workspace
and makes you its owner.

**A supported file.**

| Instrument | Extension | Max size (web upload) | Max size (File Agent) |
| --- | --- | --- | --- |
| Orbitrap | `.raw` | 2.5 GB | 100 MB |
| Tofwerk TOF | `.h5` | 2.5 GB | 100 MB |

**A filename Mascope can read.** Mascope reads three things out of the filename,
so uploads are rejected if any is missing. This applies to both upload paths.
Name files as:

```
<instrument>_<timestamp>_<ionization-token>...<.raw|.h5>
```

- **Instrument** — the first segment, before the first underscore. It must
  identify the instrument type: names containing `orbi` are treated as Orbitrap,
  and names containing `tof` or `api` as TOF. The instrument type must match the
  extension (`orbi…` with `.raw`, `tof…` with `.h5`). Use only letters, digits,
  and hyphens in this segment.
- **Timestamp** — an acquisition date/time somewhere in the name, in one of the
  recognised forms (for example `20240115_1430`, `20240115143000`, or
  `2024.01.15-14h30m00s`). Mascope uses it to place and order the file.
- **Ionization token** — the short token of a configured **ionization mode** must
  appear in the name. This is how Mascope knows how the sample was ionized.

**Configured ionization modes.** Because the filename must contain a known
ionization token, the ionization modes you use have to exist first. This is a
prerequisite in its own right — see [Set up ionization modes](#set-up-ionization-modes)
below.

**A place to process into.** Processing creates samples inside a **batch**, which
lives in a **dataset** inside a **workspace**. If you do not have an analysis
dataset and batch yet, create them in the sample browser (the left-hand panel)
before you process — you can create the workspace, dataset, and batch there.

## Set up ionization modes

An **ionization mode** tells Mascope how a measurement was ionized, and it is
what links a raw file to the right processing. Its filename token is what lets
Mascope recognise and process an uploaded file, so the modes you acquire under
must be configured before you import. See
[Concepts → Ionization](../concepts/index.md#ionization-modes-and-mechanisms) for
what a mode represents.

Open the **Raw files** tab and click **Edit ionizations** to open the *Edit
Ionization Settings* dialog. It has two tabs: **Ionization Modes** and
**Ionization Mechanisms**.

**1. Define the mechanisms first (Ionization Mechanisms tab).** A mechanism is a
single charge-forming reaction, written as `[modification][polarity]` — the
composition change followed by the ion polarity. For example `+H+` is protonation
in positive mode, `-H-` is deprotonation in negative mode, and `+Br-` is a
bromide adduct in negative mode. A mode can only use mechanisms of its own
polarity, so make sure the ones you need exist.

**2. Create the mode (Ionization Modes tab).** Fill in the *Create New Ionization
Mode* form:

| Field | Required | What it is |
| --- | --- | --- |
| **Mode Name** | Yes | A descriptive name for the mode. |
| **Filename token** | For imports | The token to look for in filenames. Without it, files acquired in this mode cannot be recognised on upload. |
| **Polarity** | Yes | `+` or `-`. Choose this first — it filters the available mechanisms. |
| **Mechanisms** | Yes | One or more mechanisms of the chosen polarity. |
| **Calibration Collection** | Optional | A [calibrants](../concepts/index.md#targeted-analysis) collection used to calibrate the mass axis for samples in this mode. |
| **Diagnostic Collection** | Optional | A [diagnostics](../concepts/index.md#targeted-analysis) collection used to monitor instrument health. |

Click **Create**. The calibrant and diagnostic collections are optional, but
setting a calibrant collection is what lets Mascope calibrate samples acquired in
this mode — add it if you intend to calibrate.

!!! note "Who can change modes"
    Any **editor** can create a mode. **Editing or deleting** a mode requires
    **admin**, because it affects every sample already processed under it —
    changing the calibrant collection flags the affected batches for
    re-calibration, and changing the mechanisms or diagnostic collection flags
    them for re-matching.

## Get the raw files in

### Automatically, with the File Agent

The **File Agent** is a small program that runs on the instrument PC, watches an
acquisition folder, and uploads new files to Mascope as they are written. This is
the recommended path for routine acquisition — once it is set up, files arrive in
Mascope with no manual step. The same filename rules above apply, so name your
acquisition method's output accordingly.

Installing, pairing, and configuring the agent (the watched folder, the file
pattern, upgrades, and troubleshooting) is covered in full on the
[Instruments & acquisition](../instruments/index.md) page. Note that the File
Agent skips files larger than 100 MB; upload those from the web app instead.

### Manually, from your computer

To import files you already have on your machine:

1. Open the **Raw files** tab (top-right of the dashboard).
2. Either click **Upload** and pick your files, or drag them onto the pane. You
   can add many files at once (up to 2.5 GB each).
3. Mascope validates each file's name against the rules above. Anything it cannot
   read (unknown instrument prefix, wrong extension, or no matching ionization
   token) is listed as invalid and left out; fix the name and try again.
4. Watch the progress notification until the uploads finish.

However they arrive, uploaded files appear in the raw-files table (listed by
filename, polarity, and datetime) and are stored in the instrument's
`Acquisitions <instrument>` workspace. Uploading does **not** yet create anything
you can analyse — that is the next step.

!!! tip "Finding files after upload"
    The table shows one time window at a time (default: the last 24 hours). Use
    the time-range and polarity filters and the filename search at the top of the
    tab to locate older files.

## Process the files into samples

Processing summarises the chosen part of each raw file into a **sample** (peaks
detected, ready to calibrate and match) and places it in a batch.

1. In the sample browser on the left, open the **dataset** and select the
   **batch** you want the samples to go into. (The batch has to be selected — the
   **Process selected** button stays disabled until it is.)
2. Back in the **Raw files** tab, select the raw files to process. Select files of
   a single polarity, or pick a polarity from the dropdown if a file contains both.
3. Click **Process selected**:
   - **One file** opens a dialog to create a single sample from it.
   - **Several files** opens the batch-import dialog, where you paste per-sample
     metadata (sample **name** and **type** are required; a **filter ID** and any
     extra attributes are optional) from a spreadsheet or autosampler report. The
     dialog previews the samples and flags any issues before you confirm.
4. Confirm. Mascope processes the files — you will see progress in the batch — and
   the new samples appear in the batch, tagged with the ionization mode read from
   each filename.

## What happens next

Once a batch has samples, you can:

- **Attach a target collection** and run **matching** to find and score your
  compounds in each sample — see [Concepts → Matching](../concepts/index.md#matching-and-match-scores).
- **Calibrate** the batch so *m/z* errors are meaningful — see
  [How it works → Calibration](../how-it-works/calibration.md).
- **Compare and visualise** samples in the **Batch** and **Sample** views.

## Troubleshooting

- **A file was rejected as invalid on upload.** The name is missing something
  Mascope needs. Check the instrument prefix matches the extension, that a
  timestamp is present, and that the name contains a configured ionization
  token. Add the ionization mode (or fix the name) and re-upload.
- **The filename token isn't recognised.** Confirm an ionization mode with that
  exact token exists in **Edit ionizations → Ionization Modes**, and that the
  token field is filled in (a mode with no token cannot match a filename).
- **"Process selected" is greyed out.** Select a batch in the sample browser
  first, then select at least one raw file. If a file has mixed polarity, choose a
  polarity from the dropdown.
- **A file needs re-processing.** Right-click it in the raw-files table and choose
  **Re-process** to rebuild its acquisition data under the current ionization
  modes. This is only available for files not tied to a batch you created.
- **Uploads from the File Agent keep failing.** See the File Agent's
  [troubleshooting section](../instruments/index.md#troubleshooting-uploads) —
  it covers rejected tokens, HTTP 404s, and the 100 MB size limit.
