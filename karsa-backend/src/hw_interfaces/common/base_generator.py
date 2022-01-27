import os
import inspect
from time import time, sleep
from ntpath import basename
from threading import Thread
from multiprocessing import Event

from karsalib.util import copy_dict, generate_unique_key
from services.FileIoService import zarr_sdk

MAX_RESPONSE_TIME = 5       # secs to wait for notification acknowledgement
PROGRESS_SHIFT = 10         # shift with acknowledged progress


def strip_filepath(filepath):
    # Strip file path and extension
    return os.path.splitext(basename(filepath))[0]


class BaseFileStreamer(Thread):
    """Base class for file streamers.
    """
    def __init__(self, client):
        self.log('Initializing', self.__class__.__name__)
        self.interval = None            # data acq interval [s]
        self.length = None              # full acq data length [s]
        self.speci = -1                 # Index of last received spectrum: -1 when no acquisition
        self.filename = None                            # streamed filename
        self.target_filename = None                     # streamer's target name
        self.item = None                                # data item to stream/store
        self.progress = 0
        self.ack_progress = -1
        self.rcontext = {}                              # generator request context
        self.fdata = {}                                 # file data
        self.client = client                            # StreamerClient - generator's parent
        self.requests = client.requests                 # Queue for files to stream
        self.responses = client.responses               # Queue for streamers notifications
        self.shutdown_event = client.shutdown_event     # Set to break out from main loop
        self.cancel_event = Event()                     # Set to cancel current stream
        Thread.__init__(self)

    def log(self, *arg, **kwarg):
        print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg, **kwarg)

    def initialize(self):
        """Initialize acquisition attributes
        """
        def init_sample_data():
            self.filename = self.fdata['filename']
            self.target_filename = '_'.join([self.client.instrument_name, self.filename]).replace(' ', '_')
            self.attrs = self.fdata['attrs']    # attrs normally contain sci data coming along with the sample
            self.project = self.attrs.get('project', None)
            self.experiment = self.attrs.get('experiment', None)
            if 'title' not in self.attrs:
                self.attrs['title'] = self.filename
        init_sample_data()
        self.request_id = self.rcontext['request_id']
        self.client_room = self.rcontext['client_room']
        self.job_id = (self.client_room, self.filename)
        with self.client.lock:
            self.client.in_progress[self.job_id] = self

    def reset(self):
        """Reset acquisition attributes
        """
        def reset_sample_data():
            self.filename = None
            self.target_filename = None
            self.project = None
            self.experiment = None
        with self.client.lock:
            self.client.in_progress.pop(self.job_id, None)
        self.request_id = None
        self.job_id = None
        reset_sample_data()
        self.item = None
        self.rcontext = {}
        self.fdata = {}
        self.progress = 0
        self.ack_progress = -1
        self.speci = -1

    def finalize(self):
        """Finalize acquisition
        """
        self.feed_final_data()
        if self.item and not self.cancel_event.is_set() and not self.shutdown_event.is_set():
            self.wait_for_ack()     # wait till all packages are processed
        self.reset()

    def wait_for_ack(self, progress_shift=0, timeout=MAX_RESPONSE_TIME):
        res = True
        t0 = time()
        while self.progress - self.ack_progress > progress_shift:
            if time() - t0 > timeout:
                self.log(f"Warning: {self.filename} - no progress acknowledgement for {timeout} sec.")
                res = False
                break
            sleep(.3)
        return res

    def get_next_file_to_stream(self):
        # get next request to process
        with self.client.lock:
            rdata = self.requests.cache_get()
        if not rdata or not rdata['files']:
            return None, None
        fdata = rdata['files'].pop(0)
        rcontext = copy_dict(rdata, ignore_keys=['files',])
        if rdata['files']:
            # not all requested files are processed - put request back to queue
            self.requests.cache_put(rdata)
        return rcontext, fdata

    def run_as_daemon(self):
        Thread(target=self.run).start()

    def shutdown(self):
        """Shutdown procedure
        """
        self.client.shutdown_event.set()

    def stop_stream(self):
        """Stop stream before complete
        """
        self.cancel_event.set()

    def run(self):
        # Main loop; virtual method
        pass

    #======== Streamer service communication protocol implementation ===============
    def feed_notifications(self, gen_notifications, streamer_notifications):
        # gen_notifications are sent always, and streamer_notifications
        # are sent in streamer mode, when target_data_pool_path is None
        if self.client.target_data_pool_path:
            notifications = gen_notifications
        else:
            notifications = [*gen_notifications, *streamer_notifications]
        for n in notifications:
            n['context']['request_id'] = self.request_id
            job_id_data = {'client_room':self.client_room, 'filename':self.filename}
            n.update(job_id_data)   # job_id_data needed for CacheQ indexing of self.responses
            self.responses.cache_put(n)

    def feed_initial_data(self):
        progress_data = {
            'client_room': self.client_room,
            'source_filename': self.filename,
            'target_filename': self.target_filename,
            'progress': self.progress,
            'ack_progress': self.ack_progress,
        }
        sn_data = {
            'name': 'acquisition_coordinates',
            'value': {
                'filename': self.target_filename,
                'mz': self.mz.tobytes(),
                't_range': [0, self.length]
            },
        }
        gen_notifications = [
            {   # TODO: remove acquisition_status for acquisition_started
                'name': 'acquisition_status',
                'value': 'running',
                'context': {
                    **self.rcontext,
                    'room': None,
                },
            },
            {
                'name': 'acquisition_started',
                'value': {
                    'filename': self.target_filename,
                    'mz_range': [float(self.mz[0]), float(self.mz[-1])],
                    't_range': [0, self.length],
                    'project': self.project,
                    'experiment': self.experiment,
                },
                'context': {
                    **self.rcontext,
                    'room': None,
                },
            },
            {
                'name': 'acquisition_progress',
                'value': progress_data,
                'context': {
                    **self.rcontext,
                    'room': None,
                },
            },
        ]
        streamer_notifications = [
            {
                **sn_data,
                'context': {
                    **self.rcontext,
                    'room': None,
                    'callback': 'cb_progress',
                    'callback_data': progress_data,
                },
            },
            {  # TODO: remove this public notification after moving DataViz to private_ns
                **sn_data,
                'context': {
                    **self.rcontext,
                    'namespace': '/',
                    'room': None,
                },
            },
        ]
        self.feed_notifications(gen_notifications, streamer_notifications)
        if self.client.target_data_pool_path:
            self.item = zarr_sdk.init_signal_dataset(sn_data, self.client.target_data_pool_path)
            self.ack_progress = self.progress

    def feed_spec_data(self, spec_data):
        progress_data = {
            'client_room': self.client_room,
            'source_filename': self.filename,
            'target_filename': self.target_filename,
            'progress': self.progress,
            'ack_progress': self.ack_progress,
        }
        sn_data = {
            'name': 'acquired_spectrum',
            'value': {
                **spec_data,
                'filename': self.target_filename,
            },
        }
        gen_notifications = [
            {
                'name': 'acquisition_progress',
                'value': progress_data,
                'context': {
                    **self.rcontext,
                    'room': None,
                },
            },
        ]
        streamer_notifications = [
            {
                **sn_data,
                'context': {
                    **self.rcontext,
                    'room': None,
                    'callback': 'cb_progress',
                    'callback_data': progress_data,
                },
            },
            {  # TODO: remove this public notification after moving DataViz to private_ns
                **sn_data,
                'context': {
                    **self.rcontext,
                    'namespace': '/',
                    'room': None,
                },
            },
        ]
        if self.client.target_data_pool_path:
            # target_data_pool_path specified - store data locally
            zarr_sdk.update_signal_dataset(sn_data, self.item)
            if self.item['signal'].delayed_write is None:
                # updates to signal mfzarrs are committed - notify
                dataset_updated = {
                    # TODO: switch to private notification after moving DataViz to private_ns
                    'name': 'dataset_updated',
                    'value': {
                        'data_type': 'signal',
                        **self.item['props'],
                    },
                    'context': {
                        **self.rcontext,
                        'namespace': '/',
                        'room': None,
                    },
                }
                gen_notifications.append(dataset_updated)
            # if data is stored locally, ack_progress is set locally,
            # otherwise by acquired_spectrum callback
            self.ack_progress = self.progress
        self.feed_notifications(gen_notifications, streamer_notifications)

    def feed_final_data(self):
        sn_data = {
            'name': 'acquisition_finished',
            'value': {
                'filename': self.target_filename,
            },
        }
        gen_notifications = [
            {   # TODO: remove acquisition_status for acquisition_finished
                'name': 'acquisition_status',
                'value': 'not_running',
                'context': {
                    **self.rcontext,
                    'room': None,
                },
            },
            {   # acquisition_finished for progress bar
                **sn_data,
                'context': {
                    **self.rcontext,
                    'room': None,
                },
            },
        ]
        streamer_notifications = [
            {  # TODO: remove this public notification after moving DataViz to private_ns
                **sn_data,
                'context': {
                    **self.rcontext,
                    'namespace': '/',
                    'room': None,
                },
            },
        ]
        if self.client.target_data_pool_path and self.item:
            try:
                zarr_sdk.finalize_signal_dataset(sn_data, self.item)
                self.client.target_data_pool.add_file(self.target_filename)
            except:
                pass    # let client services finalize the request anyway
            # updates to signal mfzarrs are finalized - notify
            dataset_updated = {
                # TODO: switch to private notification after moving DataViz to private_ns
                'name': 'dataset_updated',
                'value': {
                    'data_type': 'signal',
                    **self.item['props'],
                },
                'context': {
                    **self.rcontext,
                    'namespace': '/',
                    'room': None,
                },
            }
            gen_notifications.append(dataset_updated)
        if all([self.project, self.experiment]):
            # save sample data to experiment, if project/experiment defined in request
            sample_data = {
                'filename': self.target_filename,
                'experiment': self.experiment,
                'project': self.project,
                'attributes': [{'label': k, 'value': v} for (k,v) in self.attrs.items()],
                'method': None,
            }
            sample_to_save = {
                'name': 'save_sample',
                'value': sample_data,
                'context': {
                    **self.rcontext,
                    'namespace': '/',
                    'room': None,
                },
            }
            gen_notifications.append(sample_to_save)
        self.feed_notifications(gen_notifications, streamer_notifications)
    # ===Streamer service communication protocol implementation end=================
