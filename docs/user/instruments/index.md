# Instruments & acquisition

Operator-facing: connecting instruments, running acquisitions, and getting data
into Mascope.

## The File Agent

The File Agent is a small Windows program that runs on the instrument PC. It
watches a folder for new data files (for example Orbitrap `.raw` files) and
uploads them to your Mascope server automatically.

### Installing

1. Download the installer on the instrument PC. In the Mascope web app, open
   the sidebar via your profile icon and click **Download File Agent
   installer** under **API Access Tokens** (or download
   `Mascope-File-Agent-Setup.exe` from the latest [Mascope release on
   GitHub](https://github.com/karsa-oy/mascope/releases/latest)).
2. Before you start, generate an access token:
   1. Log in to Mascope in your browser. Your account needs the *editor* role
      or higher.
   2. Click your profile icon to open the sidebar.
   3. Under **API Access Tokens**, select **File Agent** and generate a token.
   4. Copy the token — it is shown only once.
3. Run the installer. It needs no administrator rights and offers a
   **Start the File Agent automatically when you sign in to Windows**
   checkbox — leave it enabled so the agent survives reboots.

   > The installer is not yet code-signed, so Windows SmartScreen may warn
   > about an unrecognized app. Click **More info** → **Run anyway**.

4. When the agent first starts, a guided setup runs in the console window
   and asks for:
   - the **Mascope server address** (for example `mascope.example.com`),
   - the **access token** you just generated,
   - the **folder to watch** for new data files,
   - the **file pattern** to upload (default `*.raw`).

The setup checks the server connection and the token immediately, so a typo
is caught before any data acquisition depends on it. After setup completes,
the agent starts watching the folder right away.

Leave the console window open while acquiring — closing it stops the agent
until the next sign-in (or until you start it again from the Start Menu).

### Changing the configuration

All settings live in one file on the instrument PC:

```
%APPDATA%\Mascope\FileAgent\config.toml
```

| Setting           | Meaning                                                            |
| ----------------- | ------------------------------------------------------------------ |
| `host`            | Mascope server address, e.g. `mascope.example.com`                 |
| `access_token`    | API access token generated in the Mascope web app                  |
| `source`          | Full path of the folder watched for new data files                 |
| `mask`            | Pattern of the files to upload, e.g. `*.raw`                       |
| `timeout`         | Seconds a file must be idle before it is uploaded                  |
| `filename_prefix` | Optional prefix added to the filename on upload                    |
| `filename_suffix` | Optional suffix added to the filename on upload (before extension) |

Restart the agent after editing the file. Alternatively, run the guided setup
again by starting the agent with the `--setup` flag:

```
Mascope-File-Agent.exe --setup
```

### Upgrading

Download and run the newest installer — it replaces the previous version in
place and your settings are kept. Installs made with older agent versions
(before the installer existed) are migrated automatically on first start.
The agent prints its version when it starts, and uninstalling (Windows
**Settings → Apps**) never removes your configuration.

### Troubleshooting uploads

- Logs are written to `%APPDATA%\Mascope\FileAgent\logs\prod\`.
- If an upload keeps failing, the file is copied to a `failed_uploads`
  subfolder inside the watched folder. After fixing the cause (network,
  token), copy the file back into the watched folder to retry.
- *"The server rejected the access token"*: generate a new **File Agent**
  token in the web app and update `access_token` in the configuration (or
  re-run `--setup`). Note that generating a new token invalidates your
  previous File Agent token, including on other machines using it.
- Files larger than 100 MB are not uploaded; they are logged and copied to
  `failed_uploads`.

<!-- TODO Phase 3. Outline:
- Acquisition workflow (Orbitrap, TOF)
- How uploaded files become ACQUISITION datasets/batches/samples
Cross-reference the developer agent docs in docs/dev/.
-->
