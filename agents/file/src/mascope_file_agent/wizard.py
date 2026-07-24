"""Interactive first-run setup for the bundled File Agent.

Runs in the agent's console window when required settings are missing (or
when started with ``--setup``), prompting for the server address, access
token and watched folder. The token is verified against the server right
away so typos surface during setup instead of at the first upload.
"""

import os

import requests
import urllib3

from .config import base_url, normalize_host


# Agents talk to servers with self-signed certificates (verify=False).
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

VERIFY_TIMEOUT = 15  # seconds


def verify_connection(host: str, access_token: str) -> tuple[bool, str]:
    """Check that the server is reachable and accepts the access token.

    Calls a cheap authenticated endpoint with the file-agent service
    headers, exactly as uploads will.

    :param host: Normalized server host
    :type host: str
    :param access_token: The access token to verify
    :type access_token: str
    :return: (ok, user-facing error message when not ok)
    :rtype: tuple[bool, str]
    """
    url = f"{base_url(host)}/api/sample/files"
    try:
        resp = requests.get(
            url,
            params={"page": 1, "limit": 1},
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Service-Name": "file-agent",
            },
            verify=False,
            timeout=VERIFY_TIMEOUT,
        )
    except requests.exceptions.Timeout:
        return False, f"The server at {base_url(host)} did not respond in time."
    except requests.exceptions.RequestException as e:
        return False, (
            f"Could not connect to {base_url(host)}.\n"
            f"Details: {e.__class__.__name__}: {e}"
        )
    if resp.status_code == 200:
        return True, ""
    if resp.status_code in (401, 403):
        return False, (
            "The server rejected the access token. Generate a new 'File Agent' "
            "token in the Mascope web app and try again."
        )
    return False, f"Unexpected response from the server (HTTP {resp.status_code})."


def _prompt(label: str, default: str = "") -> str:
    """Prompt for a value, offering a default when one exists.

    :param label: Prompt label
    :type label: str
    :param default: Value returned on empty input
    :type default: str
    :return: The entered (or default) value, stripped
    :rtype: str
    """
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{label}{suffix}: ").strip() or default
        if value:
            return value
        print("  A value is required.")


def _prompt_source(default: str) -> str:
    """Prompt for the watched folder, offering to create it if missing.

    :param default: Previously configured folder, if any
    :type default: str
    :return: Path of an existing directory
    :rtype: str
    """
    while True:
        source = os.path.expandvars(
            os.path.expanduser(_prompt("Folder to watch for new data files", default))
        )
        if os.path.isdir(source):
            return source
        answer = input(f"  {source} does not exist. Create it? [y/N]: ").strip().lower()
        if answer == "y":
            try:
                os.makedirs(source, exist_ok=True)
                return source
            except OSError as e:
                print(f"  Could not create the folder: {e}")


def run_setup_wizard(settings: dict) -> dict:
    """Interactively collect and verify the agent settings.

    :param settings: Current settings; non-empty values become defaults
    :type settings: dict
    :return: The completed settings dict
    :rtype: dict
    """
    print(
        "\n"
        "=== Mascope File Agent setup ===\n"
        "\n"
        "The agent watches a folder and uploads new data files to your\n"
        "Mascope server. You will need an API access token:\n"
        "\n"
        "  1. Log in to Mascope in your browser (editor role or higher)\n"
        "  2. Click your profile icon to open the sidebar\n"
        "  3. Under 'API Access Tokens', select 'File Agent' and generate\n"
        "     a token, then copy it (it is shown only once)\n"
    )

    host = normalize_host(_prompt("Mascope server address", settings.get("host", "")))
    access_token = _prompt("Access token", settings.get("access_token", ""))

    while True:
        print("Checking the connection...")
        ok, message = verify_connection(host, access_token)
        if ok:
            print("Connected - the server accepted the access token.\n")
            break
        print(f"\n{message}\n")
        choice = (
            input("Re-enter [t]oken, [s]erver address, or [c]ontinue anyway? [t/s/c]: ")
            .strip()
            .lower()
        )
        if choice == "s":
            host = normalize_host(_prompt("Mascope server address", host))
        elif choice == "c":
            print("Continuing without verification.\n")
            break
        else:
            access_token = _prompt("Access token", access_token)

    source = _prompt_source(settings.get("source", ""))
    mask = _prompt("Pattern of files to upload", settings.get("mask") or "*.raw")

    return {
        **settings,
        "host": host,
        "access_token": access_token,
        "source": source,
        "mask": mask,
    }
