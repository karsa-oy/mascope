"""
FileStreamer Service
"""

import os
import re
from datetime import datetime

from karsalib.client import (
                        BaseClientNamespace,
                        BaseStreamerClient,
                        run_streamer_service
                        )
from karsalib.util import get_client_notification_context
from karsalib.logging import Logger, parent_func_name


class FileStreamerPublicNamespace(BaseClientNamespace):
    # raw service public (root) interfaces
    # the public namespace is primarily exposed to the root namespace
    # via a room_instrument = private_namespace_name.
    room_instrument = None
    room_data_sources = 'room_data_sources'

    endpoints = []
    endpoints_room_sid = []
    endpoints_room_data_sources = [
        'instrument_data_request',
        ]
    endpoints_room_instrument = [
        'instrument_data_request',
        ]

    service_state = dict(
        instrument_data = dict(),
        )

    async def subscribe(self):
        if self.endpoints:
            await super().subscribe(self.endpoints
                                    )
        if self.endpoints_room_sid:
            await super().subscribe(self.endpoints_room_sid,
                                    self.room_sid
                                    )
        if self.endpoints_room_data_sources:
            await super().subscribe(self.endpoints_room_data_sources,
                                    self.room_data_sources
                                    )
        if self.endpoints_room_instrument:
            await super().subscribe(self.endpoints_room_instrument,
                                    self.room_instrument
                                    )

    async def on_instrument_data_request(self, data):
        await self.emit_client_notification(
                                    'instrument_data',
                                    self.parent.instrument_data,
                                    **get_client_notification_context(data)
                                    )


class FileStreamerPrivateNamespace(BaseClientNamespace):
    # raw service private interfaces
    endpoints = [
            'raw_import',
            'raw_import_status',
            'stop_raw_import',
            # 'raw_stream_request',
            'import_raw_table_datetime_range',
            'service_state'
            ]

    service_state = dict(
        instrument_status = 'not_ready',
    )

    async def on_import_raw_table_datetime_range(self, data):
        kwargs = get_client_notification_context(data)
        dt0_json = data['value'].get('dt0', '')
        dt1_json = data['value'].get('dt1', '')
        if dt0_json == '' or dt1_json == '':
            print("Either start or end datetime not given")
            return
        try:
            dt0 = datetime.strptime(dt0_json, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            print("dt0 not valid JSON datetime")
            return
        try:
            dt1 = datetime.strptime(dt1_json, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            print("dt1 not valid JSON datetime")
            return
        raw_sample_table = await self.parent.data_pool.get_datetime_range(dt0, dt1)
        await self.emit_client_notification('raw_samples',
                                            raw_sample_table,
                                            **{**kwargs,
                                               'room': data['client_room'],
                                               }
                                            )

    def get_src_data(self, fname):
        data_root = self.parent.data_pool.pool_attrs.get('path', '.')
        fdate, ftime = re.split('-|_', os.path.splitext(fname)[0])[-2:]
        path = os.path.join(data_root, fdate)
        full_fname = os.path.join(path, fname)
        size = round((os.path.getsize(full_fname)) / 2**20, 2)  # in MB
        return {'filename': fname, 'path': path, 'filesize': size, 'datetime': f'{fdate} {ftime}'}

    async def _create_generator_request(self, data):
        kwargs = get_client_notification_context(data)
        rdata = {**kwargs, 'files': []}
        for v in data['value']:
            try:
                fdata = self.get_src_data(v['filename'])
            except Exception as e:
                await self.parent.push_alert(str(e))
                raise
            rdata['files'].append({**v, **fdata})
        return rdata

    async def on_raw_import(self, data):
        rdata = await self._create_generator_request(data)
        with self.parent.lock:
            # keep single set of files for client_room in requests CacheQ
            self.parent.requests.cache_delete_key(rdata['client_room'])
            self.parent.requests.cache_put(rdata)

    async def on_raw_import_status(self, data):
        import time
        with self.parent.lock:
            kwargs = get_client_notification_context(data)
            client_room = data['client_room']
            progress_data = []
            for (c_room, f_name), streamer in self.parent.in_progress.items():
                if c_room != client_room:
                    continue
                pdata = dict(
                    filename=streamer.filename,
                    target_filename=streamer.target_filename,
                    progress=streamer.progress,
                    ack_progress=streamer.ack_progress,
                )
                progress_data.append(pdata)
            raw_import_data = {
                'progress': progress_data,
                'queue': self.parent.requests.cache.get(client_room, [{}])[0],
            }
        await self.emit_client_notification('raw_import_status_data',
                                            raw_import_data,
                                            **{**kwargs,
                                               'room': data['client_room'],
                                               }
                                           )

    async def on_stop_raw_import(self, data):
        # Without data.value, stop streaming files in progress,
        # otherwise stop files or remove files from import list by filenames
        client_room = data['client_room']
        value = data['value']
        with self.parent.lock:
            if not value:   # stop all running imports by client_room
                for (c_room, f_name), streamer in self.parent.in_progress.items():
                    if c_room != client_room:
                        continue
                    self.log(c_room, f_name)
                    streamer.stop_stream()
                    self.parent.responses.cache_delete_key(client_room)
            else:   # stop all running imports by filenames
                for v in value:
                    # remove fname from import lists if there
                    filename = v['filename']
                    full_filename = os.path.join(v['path'], filename)
                    #TODO: possible sync problem - modify CacheQ for get(key) operation
                    # clean up the fname from requests[client_room]
                    rdata = self.parent.requests.cache.get(client_room, [{}])[0]
                    i = 0
                    while i < len(rdata.get('files', [])):
                        fdata = rdata['files'][i]
                        if fdata['filename'] == full_filename:
                            rdata['files'].pop(i)
                            self.log(filename)
                        else:
                            i += 1
                    # stop importing fname, if in_progress
                    in_progress_key = (client_room, filename)
                    streamer = self.parent.in_progress.get(in_progress_key, {})
                    if streamer:
                        streamer.stop_stream()
                        self.log(filename)
                    # clean up fname from already queued responses, if any
                    try:
                        self.parent.responses.cache_delete_key(self.parent.responses.cache_key_separator.join([client_room, filename]))
                    except KeyError:
                        pass
                rdata = self.parent.requests.cache.get(client_room)
                # delete request altogether, if no files left to handle
                if rdata and not rdata[0].get('files'):
                    self.parent.requests.cache_delete_key(client_room)

    def cb_progress(self, data):
        if not data:
            return
        job_id = (data['client_room'], data['source_filename'])
        streamer = self.parent.in_progress.get(job_id)
        if streamer:
            streamer.ack_progress = data['progress']


class FileStreamerServiceClient(BaseStreamerClient):
    async def push_alert(self, msg, room=None, namespace=None):
        await self.push_log.error(f"[{self.__class__.__name__}.{parent_func_name()}] {msg}", room=room, namespace=namespace)

    async def init_service(self):
        self.push_log = Logger(self.__class__.__name__, f_log_level=None)
        self.push_log.configure_notifications(sender=self.private_ns)
        await super().init_service()
        assert self.data_pool, 'Missing data_pool argument'
        await self.data_pool.scan_dir()

    def on_filesystem_object_created(self, path):
        try:
            self.data_pool.add_file(path)
            self.log(path)
        except ValueError:
            pass

    def on_filesystem_object_deleted(self, path):
        try:
            self.data_pool.remove_file(path)
            self.log(path)
        except Exception as e:
            self.log(str(e))


def run():
    run_streamer_service(FileStreamerServiceClient,
                         FileStreamerPublicNamespace,
                         FileStreamerPrivateNamespace
                        )


if __name__ == '__main__':
    run()