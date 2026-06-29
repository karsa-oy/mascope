import shutil
from pathlib import Path

import typer

import mascope_cli.cmd.lib as lib
from mascope_cli.runtime import runtime


cert_app = typer.Typer()


@cert_app.callback()
def main():
    """
    Manage Mascope SSL certificates
    """


@cert_app.command()
def gen():
    """
    Generate a self-signed SSL certificate

    Writes mascope.app.key + mascope.app.pem into .runtime/secrets/. Use for
    local HTTPS prod testing or a small LAN deployment (clients see a
    self-signed warning). For a localhost-only trial, prefer HTTP
    (docker-compose.release.yaml) instead.
    """
    secrets_dir = Path(runtime.path(".runtime", "secrets"))
    secrets_dir.mkdir(parents=True, exist_ok=True)

    key_path = secrets_dir / "mascope.app.key"
    pem_path = secrets_dir / "mascope.app.pem"

    # Docker creates an empty DIRECTORY at a missing `file:` secret source, which
    # then blocks openssl from writing the file. Clear any such placeholders.
    for path in (key_path, pem_path):
        if path.is_dir():
            shutil.rmtree(path)

    # Use forward-slash (posix) paths: lib.run shlex-splits the command, which
    # mangles Windows backslashes. openssl accepts forward slashes on Windows.
    command = (
        "openssl req "
        + "-x509 "
        + "-nodes "
        + '-subj "/CN=mascope.app" '
        + '-addext "subjectAltName=DNS:mascope.app" '
        + "-days 365 "
        + "-newkey rsa:2048 "
        + f'-keyout "{key_path.as_posix()}" '
        + f'-out "{pem_path.as_posix()}"'
    )
    lib.run(command)

    if pem_path.is_file() and key_path.is_file():
        runtime.logger.success(f"Wrote self-signed certificate to {secrets_dir}")
    else:
        runtime.logger.error(
            "Certificate generation did not produce both files. On Windows you "
            "may need to set OPENSSL_CONF, e.g. "
            '$env:OPENSSL_CONF="C:\\Program Files\\Git\\usr\\ssl\\openssl.cnf".'
        )
