import logging

from rich.logging import RichHandler

import mascope_runtime as runtime

def setup_rich_logger():
    """Cycles through uvicorn root loggers to
    remove handler, then runs `get_logger_config()`
    to populate the `LoggerConfig` class with Rich
    logger parameters.
    """

    # Remove all handlers from root logger
    # and proprogate to root logger.
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    max_length=max(*map(lambda p: len(p['name']), runtime.modules))
    prefix=f'[dim white] {name.center(max_length, ' ')} [/dim white]'

    logging.basicConfig(
        level=logging.INFO,
        format=prefix + "%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                markup=False,
                rich_tracebacks=True,
                console=runtime.logger.console
            )
        ]
    )
