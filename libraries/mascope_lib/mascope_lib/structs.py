import inspect
import time
from threading import Thread
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer


from mascope_lib.runtime import lib_runtime


class AttrDict(dict):
    """Dict object that allows accessing values like attributes
    (dot notation).
    Example:
    d = AttrDict({'a': 0})  # initialize AttrDict with a dict
    d.a                     # returns 0
    """

    def __init__(self, *args, **kwargs):
        """Initialize self"""
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class FSWatcher:
    class FSEventHandler(PatternMatchingEventHandler):
        def __init__(self, client, mask):
            self.client = client
            if not isinstance(mask, list):
                mask = [
                    mask,
                ]
            super().__init__(patterns=mask)

        def log(self, *arg):
            lib_runtime.logger.info(
                f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg
            )

        def on_created(self, event):
            try:
                self.client.on_filesystem_object_created(event.src_path)
            except AttributeError:
                pass
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
                pass

        def on_modified(self, event):
            try:
                self.client.on_filesystem_object_modified(event.src_path)
            except AttributeError:
                pass
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
                pass

        def on_deleted(self, event):
            try:
                self.client.on_filesystem_object_deleted(event.src_path)
            except AttributeError:
                pass
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
                pass

        def on_moved(self, event):
            try:
                self.client.on_filesystem_object_created(event.dest_path)
            except AttributeError:
                pass
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
                pass
            try:
                self.client.on_filesystem_object_deleted(event.src_path)
            except AttributeError:
                pass
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
                pass

    def log(self, *arg):
        lib_runtime.logger.info(
            f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg
        )

    def __init__(self, client, target_attrs, recursive=False):
        self.client = client
        self.target_attrs = target_attrs
        self.recursive = recursive
        self.observer = Observer()
        self.handler = self.FSEventHandler(self.client, self.target_attrs["mask"])

    def start(self):
        self.observer.schedule(
            self.handler, self.target_attrs["path"], recursive=self.recursive
        )
        self.observer.start()
        self.log("started watching", self.target_attrs)

    def stop(self):
        self.observer.stop()
        self.observer.join()
        self.log("stopped")

    def run(self):
        self.start()
        while not self.client.shutdown_event.is_set():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                self.log("KeyboardInterrupt")
                self.client.shutdown_event.set()
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
                pass
        self.stop()

    def run_as_daemon(self):
        Thread(target=self.run).start()
