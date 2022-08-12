import inspect
import logging
import os
import time


NO_LOGGING_DEFAULT = False
NO_DATA_LOGGING_DEFAULT = True


def parent_func_name():
    return inspect.stack()[2][3]


def t_mark(data, note=None):
    if 't_mark' not in os.environ:
        return
    if 't_mark' not in data:
        data['t_mark'] = [[note or parent_func_name(), time.time()],]
        return
    t = time.time()
    data['t_mark'][-1][-1] = round(t - data['t_mark'][-1][-1], 3)
    data['t_mark'].append([note or parent_func_name(), t])
    print('t_mark :', data['t_mark'], data.get('request_id', data.get('filename', '')))


def this_func_name():
    return inspect.stack()[1][3]


class Logger():
    # log_levels = [
    #     logging.DEBUG,
    #     logging.INFO,
    #     logging.WARNING,
    #     logging.ERROR,
    #     logging.CRITICAL,
    # ]
    def __init__(self, fname, c_log_level='INFO', f_log_level='DEBUG', mode='r+'):
        # notification sender configuration and
        # methods are borrowed from client class
        self.target_room = None
        self.emit_client_notification = None
        # logger configuration
        self.logger = logging.getLogger(fname)
        self.logger.setLevel('DEBUG')
        # console logger
        if c_log_level:
            c_handler = logging.StreamHandler()
            c_handler.setLevel(level=c_log_level)
            c_format = logging.Formatter('%(message)s')
            c_handler.setFormatter(c_format)
            self.logger.addHandler(c_handler)
        # file logger
        if f_log_level:
            try:
                f_handler = logging.FileHandler(fname + '.log', mode=mode)
                f_handler.setLevel(level=f_log_level)
                f_format = logging.Formatter('%(message)s')
                f_handler.setFormatter(f_format)
                self.logger.addHandler(f_handler)
            except FileNotFoundError:
                pass

    def configure_notifications(self, sender=None, target_room=None):
        if sender:
            self.emit_client_notification = sender.__getattribute__('emit_client_notification')
        if target_room:
            self.target_room = target_room

    def debug(self, m):
        self.logger.debug(m)

    def info(self, m):
        self.logger.info(m)

    async def warning(self, m, room=None, namespace=None):
        self.logger.warning(m)
        if self.emit_client_notification and self.logger.isEnabledFor(logging.WARNING):
            await self.emit_client_notification('service_warning', m,
                                      room=room or self.target_room,
                                      namespace=namespace,
                                      no_logging=False,
                                      no_data_logging=False)

    async def error(self, m, room=None, namespace=None):
        self.logger.error(m)
        if self.emit_client_notification and self.logger.isEnabledFor(logging.ERROR):
            await self.emit_client_notification('service_error', m,
                                      room=room or self.target_room,
                                      namespace=namespace,
                                      no_logging=False,
                                      no_data_logging=False)

    async def critical(self, m, room=None, namespace=None):
        self.logger.critical(m)
        if self.emit_client_notification and self.logger.isEnabledFor(logging.CRITICAL):
            await self.emit_client_notification('service_critical_error', m,
                                      room=room or self.target_room,
                                      namespace=namespace,
                                      no_logging=False,
                                      no_data_logging=False)

