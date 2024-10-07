import argparse

from .app import run as run_api_server


def launch():
    parser = argparse.ArgumentParser(
        description="Launch the Mascope server or file converter"
    )
    parser.add_argument("action", type=str, help="api-server or file-converter")
    args = parser.parse_args()
    if args.action == "api-server":
        run_api_server()
    elif args.action == "file-converter":
        from .file_converter.service import run as run_file_converter

        run_file_converter()
