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
    """

    command = (
        "openssl req "
        + "-x509 "
        + "-nodes "
        + '-subj "/CN=mascope.app" '
        + '-addext "subjectAltName=DNS:mascope.app" '
        + "-days 365 "
        + "-newkey rsa:2048 "
        + f'-keyout "{runtime.path()}/.runtime/secrets/mascope.app.key" '
        + f'-out "{runtime.path()}/.runtime/secrets/mascope.app.pem"'
    )
    lib.run(command)
