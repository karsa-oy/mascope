import logging
from rich.logging import RichHandler
from rich.console import Console
from rich.theme import Theme

console = Console(
    theme=Theme(
        {
            "logging.level.info": "deep_sky_blue1",
            "logging.level.warning": "orange1",
            "logging.level.error": "bold red",
        }
    )
)

from .modules import modules


def create(
    name: str, color: str, max_length: int, level=logging.INFO, markup: bool = True
):
    prefix = f"[{color}] {name.center(max_length, " ")} [/{color}]"
    logging.basicConfig(
        level=level,
        format=prefix + "%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(markup=markup, rich_tracebacks=True, console=console)],
    )
    return logging.getLogger(name)


def service(name: str, level=logging.INFO, markup: bool = True):
    max_length = max(*map(lambda p: len(p["name"]), modules))
    mod = next(m for m in modules if m["name"] == name)
    return create(mod["name"], mod["color"], max_length, level, markup)
