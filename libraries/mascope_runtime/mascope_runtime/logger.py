import logging
from rich.logging import RichHandler
from pydantic import BaseModel
from typing import Callable

from .modules import modules

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(
            markup=True,
            rich_tracebacks=True
        )
    ]
)

class MascopeLogger(BaseModel):
    info: Callable
    error: Callable
    warning: Callable
    debug: Callable
    critical: Callable

def create(name: str, color: str, max_length: int):
    format=lambda msg: f'[{color}] {name.center(max_length, ' ').upper()} [/{color}] {msg}'
    log=logging.getLogger(name)
    return MascopeLogger(
        info = lambda msg: log.info(format(msg)),
        error = lambda msg: log.error(format(msg)),
        warning = lambda msg: log.warning(format(msg)),
        debug = lambda msg: log.debug(format(msg)),
        critical = lambda msg: log.critical(format(msg))
    )

def service(name: str):
    max_length=max(*map(lambda p: len(p['name']), modules))
    mod=next(m for m in modules if m['name'] == name)
    return create(mod['name'], mod['color'], max_length)