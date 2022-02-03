"""
FileStreamer Service
"""

import os
import re
from time import sleep
import asyncio
from datetime import datetime
from ntpath import basename, dirname

from karsalib.client import (
                        BaseClientNamespace,
                        BaseStreamerClient,
                        run_streamer_service
                        )
from karsalib.util import get_client_notification_context, generate_unique_key
from karsalib.logging import Logger, parent_func_name


class FileStreamerPublicNamespace(BaseClientNamespace):
    # raw service public (root) interfaces
    # the private namespace name is primarily exposed to the root namespace
    # as room_instrument = private_namespace_name.

    service_state = dict(
        instrument_data = {'value': dict(), 'room': 'room_data_sources'},
        )

    async def on_connect(self):
        await self.enter_room(self.room_instrument)
        await super().on_connect()

    async def on_instrument_data_request(self, data):
        await self.emit_client_notification(
                                    'instrument_data',
                                    self.parent.instrument_data,
                                    **get_client_notification_context(data)
                                    )


class FileStreamerPrivateNamespace(BaseClientNamespace):
    # raw service private interfaces

    service_state = dict(
        instrument_status = {'value': 'not_ready', 'room': None},
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

    async def on_import_sample_table_datetime_range(self, data):
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
        sample_table = await self.parent.target_data_pool.get_datetime_range(dt0, dt1)
        await self.emit_client_notification('imported_samples',
                                            sample_table,
                                            **{**kwargs,
                                               'room': data['client_room'],
                                               }
                                            )

    async def on_raw_import(self, data):
        rdata = await self._create_generator_request(data)
        with self.parent.lock:
            # keep single set of files for client_room in requests CacheQ
            self.parent.requests.cache_delete_key(rdata['client_room'])
            self.parent.requests.cache_put(rdata)

    async def on_raw_import_status(self, data):
        with self.parent.lock:
            kwargs = get_client_notification_context(data)
            client_room = data['client_room']
            progress_data = []
            for (c_room, f_name), streamer in self.parent.in_progress.items():
                # if c_room != client_room:
                #     continue
                progress_data.append({
                    **streamer.fdata,
                    'progress': streamer.progress,
                    'ack_progress': streamer.ack_progress,
                    'client_room': c_room,
                })
            queue_data = []
            for c_room in self.parent.requests.cache:
                queue_data.append(self.parent.requests.cache[c_room][0])
            raw_import_data = {
                'progress': progress_data,
                'queue': queue_data,
            }
        await self.emit_client_notification('raw_import_status_data',
                                            raw_import_data,
                                            **{**kwargs,
                                               'room': client_room,
                                               }
                                           )

    async def on_stop_raw_import(self, data):
        # Without data.value, stop streaming all files,
        # otherwise stop streaming by filenames
        def stop_import_in_progress(streamer=None):
            if not streamer:
                # stop all streamers
                for streamer in self.parent.in_progress.values():
                    stop_import_in_progress(streamer)
                return
            # stop the streamer
            self.log(streamer.client_room, streamer.filename)
            streamer.stop_stream()
            # clean up filename from already queued responses, if any
            try:
                self.parent.responses.cache_delete_key(streamer.client_room, streamer.filename)
            except KeyError:
                pass

        def clear_import_list(c_room=None, filename=None):
            if not c_room:
                self.parent.requests.cache_clear()
                self.log('clear all import list')
                return
            r_data = self.parent.requests.cache[c_room][0]
            i = 0
            while i < len(r_data.get('files', [])):
                fdata = r_data['files'][i]
                if fdata['filename'] == filename:
                    r_data['files'].pop(i)
                    self.log(r_data['client_room'], filename)
                else:
                    i += 1

        value = data['value']
        with self.parent.lock:
            if not value:   # stop all imports
                clear_import_list()
                stop_import_in_progress()
            else:   # stop all running imports by filenames from both in_progress and queue lists
                keys_to_remove = []
                for fdata in value:
                    filename = fdata['filename']
                    for c_room in self.parent.requests.cache:
                        # remove filename from scheduled import list
                        clear_import_list(c_room, filename)
                        if not self.parent.requests.cache[c_room][0]['files']:  # all files deleted from the request
                            keys_to_remove.append(c_room)
                        # stop importing filename, if in_progress
                        in_progress_key = (c_room, filename)
                        streamer = self.parent.in_progress.get(in_progress_key)
                        if streamer:
                            stop_import_in_progress(streamer)
                # delete request altogether, if no files left to handle
                for c_room in keys_to_remove:
                    self.parent.requests.cache_delete_key(c_room)

    def get_src_data(self, path, fname):
        def get_h5_datetime():
            # returns ('YYYY.mm.dd', 'HH:MM:SS') for TOF h5 samples
            dt_regex = r'.*(\d{4}).(\d{2}).(\d{2}).(\d{2}).(\d{2}).(\d{2}).*\.h5'
            dt = re.findall(dt_regex, fname)[0]
            return '.'.join(dt[:3]), ':'.join(dt[3:])

        def get_raw_datetime():
            # returns ('YYYY.mm.dd', 'HH:MM') for Orbi raw samples
            dt_regex = r'^(\d{8}).(\d{4}).*\.raw'
            d, t = re.findall(dt_regex, fname)[0]
            return '.'.join([d[:4], d[4:6], d[6:]]), ':'.join([t[:2], t[2:]])

        data_root = self.parent.data_pool.pool_attrs.get('path', '.')
        try:
            fdate, ftime = get_h5_datetime()
        except IndexError:
            fdate, ftime = get_raw_datetime()
        if not path:    # path normally does not come with batch import
            path = os.path.join(data_root, fdate)
        if not os.path.isdir(path):
            path = data_root
        full_fname = os.path.join(path, fname)
        size = round((os.path.getsize(full_fname)) / 2**20, 2)  # in MB
        return {'filename': fname,
                'path': path,
                'props': {'filesize': size, 'datetime': f'{fdate} {ftime}'},
               }

    async def _create_generator_request(self, data):
        def is_reimport_request(fdata):
            return all([fdata.get('props'), fdata.get('attrs')])

        kwargs = get_client_notification_context(data)
        rdata = {**kwargs, 'files': []}
        for v in data['value']:
            fname = v['filename']
            if self.parent.is_sample_in_progress(fname):
                self.log(f"Skip {fname}: the sample is already being imported")
                continue
            if is_reimport_request(v):
                rdata['files'].append(v)
            else:
                fname = v.pop('filename')
                path = v.pop('path', None)    # path normally does not come with batch import
                try:
                    fprops = self.get_src_data(path, fname)
                except Exception as e:
                    await self.parent.push_alert(str(e))
                    raise
                # attrs normally contain sci data coming along with the sample
                rdata['files'].append({**fprops, 'attrs': v})
        return rdata

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
        if self.target_data_pool:
            await self.target_data_pool.scan_dir()

    def on_filesystem_object_created(self, path):
        try:
            self.log(path)
            self.data_pool.add_file(path)
            if self.transit:
                filename = basename(path)
                self.log('transit', filename)
                raw_sample_data = {
                    'name': 'raw_import',
                    'value': [
                        {'filename': filename, 'path': dirname(path), },
                    ],
                    'request_id': generate_unique_key(),
                    # unique client_room - for a new transit request not to replace prev.one
                    'client_room': generate_unique_key(),
                }
                sleep(3)   # let file object to be created properly
                asyncio.run(self.private_ns.on_raw_import(raw_sample_data))
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