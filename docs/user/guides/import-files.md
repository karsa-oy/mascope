# Import data files

Getting a measurement into Mascope is a two-step process: **upload** the raw
instrument file, then **process** it into one or more samples inside a batch.
This guide covers doing both from the web app. (For hands-off uploading straight
from an instrument PC, set up the [File Agent](../instruments/index.md) instead —
it uploads files automatically, and you then process them the same way.)

New to the terms *sample file*, *sample*, *batch*, and *ionization mode*? See
[Concepts](../concepts/index.md) first — this guide assumes them.

## Prerequisites

Before your first import, make sure the following are in place.

**Your access**

- An **editor** role (or higher) in the instrument's workspace. Guests can view
  and export but cannot upload or process. See
  [Authorization](https://github.com/karsa-oy/mascope/blob/master/docs/authorization.md).
  Uploading a file for a brand-new instrument creates that instrument's workspace
  and makes you its owner.

**A supported file**

| Instrument | Extension | Max size (web upload) |
| --- | --- | --- |
| Orbitrap | `.raw` | 2.5 GB |
| Tofwerk TOF | `.h5` | 2.5 GB |

**A filename Mascope can read.** Mascope reads three things out of the filename,
so uploads are rejected if any is missing. Name files as:

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

**A configured ionization mode.** Because the filename must contain a known
ionization token, the ionization modes you use have to exist first. Open the
**Raw files** tab and click **Edit ionizations** to review or add them (editor
role or higher). Each mode carries the token to look for, its polarity, its
mechanisms, and its calibrant and diagnostic collections — see
[Concepts → Ionization](../concepts/index.md#ionization-modes-and-mechanisms).

**A place to process into.** Processing creates samples inside a **batch**, which
lives in a **dataset** inside a **workspace**. If you do not have an analysis
dataset and batch yet, create them in the sample browser (the left-hand panel)
before you process — you can create the workspace, dataset, and batch there.

## Step 1 — Upload the raw files

1. Open the **Raw files** tab (top-right of the dashboard).
2. Either click **Upload** and pick your files, or drag them onto the pane. You
   can add many files at once.
3. Mascope validates each file's name against the rules above. Anything it cannot
   read (unknown instrument prefix, wrong extension, or no matching ionization
   token) is listed as invalid and left out; fix the name and try again.
4. Watch the progress notification until the uploads finish. Uploaded files then
   appear in the raw-files table, listed by filename, polarity, and datetime.

Uploaded files are stored in the instrument's `Acquisitions <instrument>`
workspace. Uploading does **not** yet create anything you can analyse — that is
the next step.

!!! tip "Finding files after upload"
    The table shows one time window at a time (default: the last 24 hours). Use
    the time-range and polarity filters and the filename search at the top of the
    tab to locate older files.

## Step 2 — Process the files into samples

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
- **"Process selected" is greyed out.** Select a batch in the sample browser
  first, then select at least one raw file. If a file has mixed polarity, choose a
  polarity from the dropdown.
- **A file needs re-processing.** Right-click it in the raw-files table and choose
  **Re-process** to rebuild its acquisition data under the current ionization
  modes. This is only available for files not tied to a batch you created.
- **Uploads from an instrument PC keep failing.** That path uses the File Agent —
  see its [troubleshooting section](../instruments/index.md#troubleshooting-uploads).
