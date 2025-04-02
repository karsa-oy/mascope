# import type hint w/o circular import error
from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
    import loguru
    from mascope_runtime import Runtime
    from .mode import RuntimeMode

from loguru import logger

import duckdb
import datetime
import os
import glob
import sys
import io
import re
import json
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
    "white": "white",
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

    @property
    def dir(self):
        """
        Resolves the logging directory
        """
        return self.runtime.module.config.log_path

    def path(self, *args: list[str]):
        """
        Resolves the path relative to the logging directory

        :param *args: A list of path segments
        :type arg: list[str], optional
        :return: Resolved path
        :rtype: str
        """
        return os.path.join(self.dir, self.runtime.mode, *args)

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
            handlers=[file_handler, terminal_handler]
            if self.runtime.module.name != "cli"
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

            status_style = self.status_style(status_code)

            # FIELDS

            # overrides
            #  see the `query` method below
            override = record["extra"].get("override")
            if override:
                timestamp = override["time"]
                record["name"] = override["name"]
                record["function"] = override["function"]
                record["line"] = override["line"]
                record["extra"] = override["extra"]
                rich_exception = override["extra"].get("rich_exception")
            else:
                timestamp = "{time:HH:mm:ss.SSS!UTC}"
                rich_exception = None

            # head
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

            # tail
            module = record["extra"]["mod"]
            module_styled = self.style(
                module, f"fg {palette[self.runtime.config.color]}"
            )
            path = record["name"]
            func = record["function"]
            func_or_module = "[module]" if func == "<module>" else func
            line = record["line"]
            key = record["extra"]["key"]
            key_span = f"❯ {key}" if key and len(key) > 0 else ""
            tail = f"{module_styled} ❯ {path} ❯ {func_or_module}:{line} {key_span}"
            tail_text = f"{module} ❯ {path} ❯ {func}:{line} {key_span}"

            # highlight grep
            full_text = f"{head_text} {message_text} {tail_text}"
            grep = os.environ.get("MASCOPE_LOGGREP", None)
            match = grep in full_text if grep else highlight.match(full_text)
            tags = ["dim"] if not match else []

            # FORMAT
            fmt = self.style(f" {head} {message} {tail}\n", *tags)

            # TRACEBACKS
            output = io.StringIO()
            console = Console(file=output)
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
            elif rich_exception:
                record["extra"]["rich_exception"] = rich_exception
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

    def status_style(self, status_code: int) -> Callable:
        """
        Construct a status styling function from a status code.

        :param status_code: the status code
        :return: a styling function
        """

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

        return status_style

    def stacktrace(self, show_locals: bool = False, skip_frames: int = 0) -> Traceback:
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

    def query(
        self,
        level: str | None = "info",
        limit: int | None = None,
        grep: str | None = None,
        grep_context=25,
        from_datetime: str = None,
        to_datetime: str | None = None,
        interval: str | None = None,
        mode: RuntimeMode | None = None,
    ):
        """
        Executes a query against dev or prod log files in the active runtime
        env.

        duckdb is used in-memory to injest all log files and filter the
        relevant fields and values.

        :param level: the log level above which to print
        :param limit: the maximum limit of the number of lines to print
        :param grep: a search pattern to filter log messages against
        :param grep_context: the number of rows before and after a `grep` match to include
        :param from_datetime: the start of the time range
        :param to_datetime: end of the time range
        :param interval: the interval of the time range
        :param mode: the runtime mode (dev or prod)
        """
        if from_datetime and to_datetime and interval:
            self.runtime.logger.error(
                "runtime.logging.query: cannot use 'from_datetime', 'to_datetime' and 'interval' together"
            )
            return

        # PREPARE - collect key variables and clauses
        log_path = os.path.join(self.dir, mode or self.runtime.mode, "*.log")
        level_no = {
            "trace": 5,
            "debug": 10,
            "info": 20,
            "success": 25,
            "warning": 30,
            "error": 40,
            "critical": 50,
        }[level]
        limit_clause = f"LIMIT {limit}" if limit else ""
        from_clause = (
            f"AND timestamp >= '{from_datetime}'::TIMESTAMP" if from_datetime else ""
        )
        to_clause = (
            f"AND timestamp <= '{to_datetime}'::TIMESTAMP" if to_datetime else ""
        )
        if interval:
            if from_clause:
                to_clause = f"AND timestamp <= '{from_datetime}'::TIMESTAMP + INTERVAL '{interval}'"
            elif to_clause:
                from_clause = f"AND timestamp >= '{to_datetime}'::TIMESTAMP - INTERVAL '{interval}'"
            else:
                from_clause = f"AND timestamp >= '{datetime.datetime.now().isoformat()}'::TIMESTAMP - INTERVAL '{interval}'"

        # BUILD - construct the queries
        base_query = f"""
            SELECT
                json_extract(json, '$.record.time.repr')::TIMESTAMPTZ as timestamp,
                json.record.level.name as level,
                json.record.level.no as level_no,
                json.record.extra.status_code as status,
                json.record.extra.method as method,
                json.record.message as message,
                json.record.extra.mod as module,
                json.record.name as path,
                json.record.function as func,
                json.record.line as line,
                json.record.extra.key as key,
                json
            FROM read_ndjson_objects('{log_path}')
            WHERE
                level_no >= {level_no}
                {from_clause}
                {to_clause}
        """
        if not grep:
            query = f"""
                WITH log AS (
                    {base_query}
                )
                SELECT
                  timestamp,
                  level,
                  message,
                  json
                FROM log
                ORDER BY log.timestamp
                {limit_clause}
            """
        elif grep:
            query = f"""
                WITH log AS (
                    {base_query}
                ),
                context AS (
                    SELECT
                        log.*,
                        STRING_AGG(
                            CONCAT_WS(' ',
                                log.level,
                                log.status,
                                log.method,
                                log.message,
                                CONCAT_WS(
                                    ' ❯ ',
                                    log.module,
                                    log.path,
                                    CONCAT(log.func, ':', log.line),
                                    log.key
                                )
                            ),
                            ' '
                        )
                        OVER (
                            ORDER BY log.timestamp ROWS
                            BETWEEN {grep_context} PRECEDING
                            AND {grep_context} FOLLOWING
                        ) as context,
                    FROM log
                    ORDER BY log.timestamp
                )
                SELECT
                  timestamp,
                  level,
                  message,
                  json
                FROM context ctx
                WHERE ctx.context LIKE '%{grep}%'
                {limit_clause}
            """

        # EXECUTE - run the query and print the logs using loguru
        with duckdb.connect() as conn:
            records = conn.sql(query).fetchall()
            for (
                timestamp,
                level,
                message,
                raw,
            ) in records:
                raw = json.loads(raw)
                override = raw["record"]
                override["time"] = timestamp.isoformat().replace("T", " ")
                # Spoof the logger to pretend to log the original
                # record rather than from here:
                (logger.bind(override=override).log(level[1:-1], message[1:-1]))
        print(
            f"\n\n  Printed {len(records)} lines of logs from {log_path.split('*')[0]}"
        )

    def gc(
        self,
        mode: RuntimeMode,
        before: str | None,
        retain: str | None,
        dryrun: bool = False,
    ) -> None:
        """
        Garbage collect stale or empty log files, either 'before' a specified date
        or excluding a time interval (in days, weeks or months) to 'retain'.

        :param mode: the runtime mode (dev or prod)
        :param before: the maximum date before which to delete log files
        :param retain: a time interval for which to keep log files
        :param dryrun: don't actually delete anything, just print a preview
        """

        if not mode:
            self.runtime.logger.error(
                "runtime.logging.gc: mode must be specified (dev or prod)"
            )
            return
        if (before and retain) or not (before or retain):
            self.runtime.logger.error(
                "runtime.logging.gc: must specify either before or retain argument (not both)"
            )
            return

        if retain:
            with duckdb.connect() as conn:
                max_date = conn.sql(
                    f"SELECT current_date - INTERVAL {retain}"
                ).fetchall()[0][0]
        elif before:
            max_date = datetime.datetime.strptime(before, "%Y-%m-%d")

        total_count = 0
        empty_count = 0
        stale_count = 0
        skip_count = 0

        prefix = "[DRY RUN] " if dryrun else ""

        log_path = os.path.join(self.dir, mode, "*.log")
        for f in sorted(glob.glob(log_path)):
            raw_date = os.path.split(f)[-1].split(".")[0]
            parsed_date = datetime.datetime.strptime(raw_date, "%Y-%m-%d")
            stale = parsed_date < max_date
            empty = os.stat(f).st_size == 0
            descs = []
            descs.append("stale" if stale else "fresh")
            descs.append("empty" if empty else "non-empty")
            if stale or empty:
                self.runtime.logger.info(f"{prefix} deleting {' & '.join(descs)}: {f}")
                if not dryrun:
                    os.remove(f)
                total_count += 1
                if stale:
                    stale_count += 1
                if empty:
                    empty_count += 1
            else:
                self.runtime.logger.info(f"{prefix} skipping {' & '.join(descs)}: {f}")
                skip_count += 1
        empty_text = "as well as empty files" if empty_count > 0 else ""
        self.runtime.logger.info(
            f"{prefix} garbage collected log files older than {max_date}{empty_text}"
        )
        self.runtime.logger.info(
            f"{prefix} deleted a total of {total_count} files: {stale_count} stale & {empty_count} empty. Skipped {skip_count} files."
        )
