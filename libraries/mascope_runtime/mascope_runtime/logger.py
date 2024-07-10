import logging
from rich.logging import RichHandler

from .modules import modules

def create(name: str, color: str, max_length: int):
    prefix=f'[{color}] {name.center(max_length, ' ').upper()} [/{color}]'
    logging.basicConfig(
        level=logging.INFO,
        format=prefix + "%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                markup=True,
                rich_tracebacks=True
            )
        ]
    )
    return logging.getLogger(name)

def service(name: str):
    max_length=max(*map(lambda p: len(p['name']), modules))
    mod=next(m for m in modules if m['name'] == name)
    return create(mod['name'], mod['color'], max_length)