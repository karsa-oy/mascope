import typer
import rich

import mascope_runtime as runtime

pretty = lambda obj: rich.pretty.pprint(obj, indent_guides=False, expand_all=True)

config = typer.Typer()


@config.callback()
def main():
    """
    Manage your mascope configurations
    """


@config.command()
def list():
    """
    List available configurations in your configuration directory
    """
    runtime.config.list()


@config.command()
def set(config: str):
    """
    Set the active configuration
    """
    runtime.state.default = config
    rich.print(f"Mascope config set to '{config}'")


@config.command()
def unset():
    """
    Unset the active configuration, defaulting to 'dev' or 'prod' configs
    """
    runtime.state.default = None


@config.command()
def show(config=None):
    """
    Show the active configuration
    """
    pretty(runtime.config.autoload())
