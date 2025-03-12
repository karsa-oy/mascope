# import type hint w/o circular import error
from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
    import loguru
    from .runtime import Runtime

from loguru import logger

import datetime
import os
import sys
import io
import re
from types import TracebackType

from rich.console import Console
from rich.traceback import Traceback

from typing import List, Callable

highlight = re.compile("SUCCESS|WARNING|ERROR|CRITICAL")

palette = {
    "magenta": "#d8137f",
    "red": "#d65407",
    "orange": "#dc8a0e",
    "green": "#17ad98",
    "blue": "#149bda",
    "purple": "#796af5",
    "pink": "#c720ca",
}

colors = {
    "cli": palette["blue"],
    "backend": palette["green"],
    "frontend": palette["orange"],
    "notebooks": palette["red"],
    "tof-agent": palette["pink"],
    "file-uploader": palette["purple"],
    "file-converter": palette["magenta"],
}


class Stacktrace:
    """
    Dummy class for printing pretty stacktraces
    """

    pass


class RuntimeLogging:
    """
    Helper class to configure the runtime logger of a
    module.

    Since loguru configuration persists across modules,
    once we execute the `configure` method, we can just
    import `logger` from Loguru and the settings will
    persist. This is what the Runtime class does when
    exposing `runtime.logger`.

    Helper methods are here are mostly for formatting
    the CLI logs nicely.

    To be used with the `configure_logger` helper
    below.
    """

    _runtime: Runtime

    def __init__(self, runtime: Runtime) -> None:
        """
        Configures the runtime logger, saving the
        result to self._logger.

        :param runtime: The parent runtime context
        :type runtime: Runtime
        """
        self._runtime = runtime

    @property
    def runtime(self):
        """
        The parent runtime context.
        """
        return self._runtime

    @property
    def logger(self):
        """
        Get the configured logger.

        :return: the logger of the runtime module
        :rtype: loguru.Logger
        """
        return logger

    def path(self, *args: list[str]):
        """
        Resolves the path relative to the logging directory

        :param *args: A list of path segments
        :type arg: list[str], optional
        :return: Resolved path
        :rtype: str
        """
        log_path = self.runtime.module.config.log_path
        return os.path.join(log_path, self.runtime.mode, *args)

    # module is not typed to prevent circular import
    def configure(self) -> None:
        """
        Configure the loguru logger, setting file and terminal logging
        handlers, log level formatting and other settings. Clears all
        previous configuration.

        :param module: the runtime module to configure the logging for
        :return: the loguru logger
        """
        # setup log path
        os.makedirs(self.path(), exist_ok=True)
        # define logging handlers
        file_handler = dict(
            sink=self.path(f"{{time:YYYY-MM-DD}}.{self.runtime.module.name}.log"),
            format=self.formatter(),
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
            format=self.formatter(),
            colorize=True,
            level=self.runtime.module.config.log_level.upper(),
            enqueue=True,  # multiprocess safe
            catch=True,
        )
        # create fresh config
        logger.remove()  # remove old settings
        logger.configure(  # apply new settings
            handlers=(
                [file_handler, terminal_handler]
                if self.runtime.module.name != "cli"
                else [terminal_handler]
            ),
            levels=[
                dict(name="TRACE", color="<magenta>"),
                dict(name="DEBUG", color="<magenta>"),
                dict(name="INFO", color="<blue>"),
                dict(name="SUCCESS", color="<green>"),
                dict(name="WARNING", color="<yellow>"),
                dict(name="ERROR", color="<red><bold>"),
                dict(name="CRITICAL", color="<RED><bold>"),
            ],
            extra=dict(mod=self.runtime.module.name, key="", status_code="", method=""),
        )
        return logger

    def formatter(self) -> Callable[[loguru.Record], str]:
        """
        Factory that produces a format function used in
        the loguru logger.

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
                    return self.style(msg, "blue")

            elif response(200):
                # successful response
                def status_style(msg):
                    return self.style(msg, "green")

            elif response(300):
                # redirection response
                def status_style(msg):
                    return self.style(msg, "cyan")

            elif response(400):
                # client error response
                def status_style(msg):
                    return self.style(msg, "bold", "yellow")

            elif response(500):
                # server error response
                def status_style(msg):
                    return self.style(msg, "bold", "red")

            else:
                # other
                def status_style(msg):
                    return self.style(msg, "magenta")

            # FIELDS

            # header
            timestamp = "{time:HH:mm:ss.SSS!UTC}"
            level = self.style("{level: >8}", "lvl")
            status = "{extra[status_code]: >3}"
            method = "{extra[method]: <7}"
            head = f"{timestamp} {level} " + status_style(f"{status} {method}")
            head_text = f"{record['level']} {record['extra']['status_code']} {record['extra']['method']}"

            # message
            record["extra"]["parsed_message"] = (
                record["message"]
                .replace(self.runtime.env.path(), "$env")
                .replace(self.runtime.path(), "$mascope")
            )
            message = "{extra[parsed_message]: <60}"
            message_text = f"{record['message']}"

            # footer
            module = self.style("{extra[mod]}", f"fg {colors[record['extra']['mod']]}")
            path = "{name}:{line}"
            key = "{extra[key]}"
            tail = f"{module} {path} {key}"
            tail_text = f"{record['name']} {record['extra']['key']}"

            # highlight search
            full_text = f"{head_text} {message_text} {tail_text}"
            grep = os.environ.get("MASCOPE_LOGGREP", None)
            match = grep in full_text if grep else highlight.match(full_text)
            tags = ["dim"] if not match else []

            # FORMAT
            fmt = self.style(f" {head} {message} {tail}\n", *tags)

            # TRACEBACKS
            output = io.StringIO()
            console = Console(file=output, force_terminal=True)
            trace_opt = record["extra"].get("trace", False)
            is_exception = record["exception"] is not None
            trace = None
            if is_exception:
                # pretty print exception traceback
                trace = Traceback.from_exception(*record["exception"])
            elif trace_opt:
                # construct stacktrace without exception
                trace = self.stacktrace(skip_frames=5)  # *
                # * we skip five frames in order to get directly to the
                # logger callsite, i.e. we avoid printing stack frames
                # from this module or loguru.
            if trace:
                # if trace exists, we add it to the message
                console.print("")
                console.print(trace)
                record["extra"]["rich_exception"] = output.getvalue()
                fmt += "{extra[rich_exception]}\n"

            # format string
            return fmt

        # return the format function
        return format_record

    def style(self, msg: str, *tags: List[str]) -> str:
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

    def stacktrace(show_locals: bool = False, skip_frames: int = 0) -> Traceback:
        """
        Constructs a pretty stacktrace for situations where
        there is no exception.

        :param show_locals: whether to show local variables in the frame
        :param skip_frames: how many frames to skip in the begining
        :return traceback: a rich Traceback object
        """
        trace = None
        depth = 1
        while True:
            try:
                frame = sys._getframe(depth)
                depth += 1
            except Exception:
                break
            if depth > skip_frames:
                trace = TracebackType(trace, frame, frame.f_lasti, frame.f_lineno)
        exception = Exception("trace for debugging purposes (not a real exception)")
        stack = Traceback.extract(Stacktrace, exception, trace, show_locals=show_locals)
        return Traceback(stack, show_locals=show_locals)
