import argparse
import os
import shutil
import sys
import time


def parse_cmd_args():
    """
    Parse command line arguments
    ------------------------------
    Return dict
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-l", "--log_file", help="path to generated log file", type=str, required=False
    )
    parser.add_argument(
        "-n",
        "--records_per_file",
        help="number of log records per log file",
        type=int,
        default=1000,
    )
    return vars(parser.parse_args())


class RotationLogger:
    def __init__(self, log_file=None, records_per_file=1000):
        self.log_file = log_file
        self.records_per_file = records_per_file
        self.record_cnt = 0

    def dump_to_file(self, *arg):
        def rotate_log():
            old_log = self.log_file + ".old"
            try:
                if os.path.isfile(old_log):
                    os.remove(old_log)
                shutil.move(self.log_file, old_log)
                return ""
            except Exception as e:
                return f"Exception: {e.__class__.__name__}({str(e)}"

        error_msg = ""
        if self.record_cnt % self.records_per_file == 0:
            error_msg = rotate_log()
        with open(self.log_file, "a") as f:
            if error_msg:
                f.write(error_msg)
            r = " ".join([f"{a}" for a in arg])
            f.write(r)

    def log(self, *arg):
        self.record_cnt += 1
        if self.log_file:
            self.dump_to_file(*arg)
        else:
            print(*arg)


def line_prefix():
    t = time.localtime(time.time())
    return f"{t.tm_hour}:{t.tm_min}:{t.tm_sec} {t.tm_mday}.{t.tm_mon}"


def run():
    kwargs = parse_cmd_args()
    logger = RotationLogger(**kwargs)
    exc_cnt = 0
    while exc_cnt < 2:
        try:
            for line in sys.stdin:
                logger.log(line_prefix(), line)
        except KeyboardInterrupt:
            # at 1st Ctrl-C don't quit - let input provider finish
            exc_cnt += 1


if __name__ == "__main__":
    # Log piped stdin to log_rotate;
    # Use 'src |& log_rotate' to pipe both stdout and stderr to stdin.
    run()
