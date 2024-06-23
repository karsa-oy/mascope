import typer

from .cmds import dev, cli

app = typer.Typer(help="🔭 Mascope development CLI")

app.add_typer(dev, name="dev")
app.add_typer(cli, name="cli")