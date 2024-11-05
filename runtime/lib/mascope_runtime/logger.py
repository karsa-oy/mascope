# for typehints
from __future__ import annotations
import loguru

from loguru import logger

import datetime
import os
import sys
import io
import re

from rich.console import Console
from rich.traceback import Traceback

from typing import List, Callable

highlight = re.compile("SUCCESS|WARNING|ERROR|CRITICAL")


def style(msg: str, *tags: List[str]) -> str:
    """
    Helper for styling log messages

    :param msg: the message to style
    :param tags: list of tags to apply to the message
    :return: styled message string
    """
    # wrap style tags around msg
    start = ""
    for tag in tags:
        start += f"<{tag}>"
    end = ""
    for tag in reversed(tags):
        end += f"</{tag}>"
    return f"{start}{msg}{end}"


def formatter(root_path: str) -> Callable[[loguru.Record], str]:
    """
    Factory that produces a format function given a
    root_path (MASCOPE_PATH) value.

    :param root_path: the MASCOPE_PATH
    :return: the record formatting function
    """

    def format_record(record: loguru.Record):
        # STATUS

        # code
        raw_status_code = record["extra"]["status_code"]
        if isinstance(raw_status_code, str):
            if len(raw_status_code):
                status_code = int(raw_status_code)
            else:
                status_code = 0
        elif isinstance(raw_status_code, int):
            status_code = raw_status_code
        else:
            status_code = 0

        # response
        def response(start):
            return start <= status_code and status_code < start + 100

        # color

        if response(100):
            # informational response
            def status_style(msg):
                return style(msg, "blue")
        elif response(200):
            # successful response
            def status_style(msg):
                return style(msg, "green")
        elif response(300):
            # redirection response
            def status_style(msg):
                return style(msg, "cyan")
        elif response(400):
            # client error response
            def status_style(msg):
                return style(msg, "bold", "yellow")
        elif response(500):
            # server error response
            def status_style(msg):
                return style(msg, "bold", "red")
        else:
            # other
            def status_style(msg):
                return style(msg, "magenta")

        # FIELDS

        # header
        timestamp = "{time:HH:mm:ss.SSS!UTC}"
        level = style("{level: >8}", "lvl")
        status = "{extra[status_code]: >3}"
        method = "{extra[method]: <7}"
        head = f"{timestamp} {level} " + status_style(f"{status} {method}")
        head_text = f"{record["level"]} {record["extra"]["status_code"]} {record["extra"]["method"]}"

        # message
        envpath = os.path.join(
            root_path, "runtime", "env", os.environ.get("MASCOPE_ENV", "prod")
        )
        record["extra"]["parsed_message"] = (
            record["message"].replace(envpath, "$env").replace(root_path, "$mascope")
        )
        message = "{extra[parsed_message]: <60}"
        message_text = f"{record["message"]}"

        # footer
        module = "{name}:{line}"
        key = "{extra[key]}"
        tail = f"{module} {key}"
        tail_text = f"{record["name"]} {record["extra"]["key"]}"

        # highlight search
        full_text = f"{head_text} {message_text} {tail_text}"
        grep = os.environ.get("MASCOPE_LOGGREP", None)
        match = grep in full_text if grep else highlight.match(full_text)
        tags = ["dim"] if not match else []

        # FORMAT
        fmt = style(f" {head} {message} {tail}\n", *tags)

        # tracebacks
        if record["exception"] is not None:
            output = io.StringIO()
            console = Console(file=output, force_terminal=True)
            traceback = Traceback.from_exception(*record["exception"])
            console.print("")
            console.print(traceback)
            record["extra"]["rich_exception"] = output.getvalue()
            fmt += "{extra[rich_exception]}\n"

        # format string
        return fmt

    # return the format function
    return format_record


# module is not typed to prevent circular import
def config_logger(module: any) -> loguru.Logger:
    """
    Configure the loguru logger, setting file and terminal logging
    handlers, log level formatting and other settings. Clears all
    previous configuration.

    :param module: the runtime module to configure the logging for
    :return: the loguru logger
    """
    # setup log path
    log_path = os.path.join(module.config.log_path, module.mode)
    os.makedirs(log_path, exist_ok=True)
    # define logging handlers
    file_handler = dict(
        sink=os.path.join(log_path, f"{{time:YYYY-MM-DD}}.{module.name}.log"),
        format=formatter(module.root_path),
        level="INFO",  # avoid large file size
        enqueue=True,  # multiprocess safe
        serialize=True,  # output as JSON
        rotation=datetime.time(
            0, 0, 0, tzinfo=datetime.timezone.utc
        ),  # rotate daily at midnight UTC
        retention=datetime.timedelta(days=14),  # retain two weeks of files
    )
    terminal_handler = dict(
        sink=sys.stdout,
        format=formatter(module.root_path),
        colorize=True,
        level=module.config.log_level.upper(),
        enqueue=True,  # multiprocess safe
        catch=True,
    )
    # create fresh config
    logger.remove()  # remove old settings
    logger.configure(  # apply new settings
        handlers=[file_handler, terminal_handler]
        if module.name != "cli"
        else [terminal_handler],
        levels=[
            dict(name="TRACE", color="<magenta>"),
            dict(name="DEBUG", color="<magenta>"),
            dict(name="INFO", color="<blue>"),
            dict(name="SUCCESS", color="<green>"),
            dict(name="WARNING", color="<yellow>"),
            dict(name="ERROR", color="<red><bold>"),
            dict(name="CRITICAL", color="<RED><bold>"),
        ],
        extra=dict(mod=module.name, key="", status_code="", method=""),
    )
    return logger
