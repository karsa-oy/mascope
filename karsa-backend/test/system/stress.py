import argparse
import os
import time
import logging
import shutil
import json
from threading import Thread, current_thread
import asyncio
import datetime_glob
from datetime import datetime
from systestlib import start_test_client_as_daemon
from karsalib.datapool import parse_path_from_sample_name

import logging
logging.basicConfig(filename=f'{os.path.splitext(os.path.basename(__file__))[0]}.log', 
                    format='%(asctime)s %(message)s', datefmt='%H:%M:%S',
                    level=logging.INFO)

MAX_STREAM_TIME_DEFAULT = 40
MAX_VIZ_TIME_DEFAULT = 30
ZOOM_RANGE_DEFAULT = 1

args = None
client = None
shutdown_event = None
viz_request_ids = []
stream_samples = ["20210122_1028_SRCI_DBrMe__1TCM.raw", "20210122_1028_SRCI_DBrMe__2TCM.raw"]
viz_samples = ["OrbitrapData_20210122_1028_SRCI_DBrMe__3TCM.raw", "OrbitrapData_20210122_1028_SRCI_DBrMe__4TCM.raw"]

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", help="backend url", type=str, default='localhost')
    parser.add_argument("-p", "--port", help="backend port", type=int, default=5010)
    parser.add_argument("-ns", "--namespace", help="File services namespace to connect", type=str, required=True)
    parser.add_argument("-vl", "--viz_list", help="filename: list of zarr samples to visualize - for viz stresstest", type=str, default=None)
    parser.add_argument("-sl", "--stream_list", help="filename: stream list of raw samples - for stream stresstest", type=str, default=None)
    parser.add_argument("-nv", "--n_viewers", help="max number of zarr sample viewers", type=int, default=0)
    parser.add_argument("-td", "--target_data_pool_path", help="target data pool path (before date dirs)", type=str, required=True)
    parser.add_argument("-mv", "--max_viz_time", help="max visualization time", type=int, default=MAX_VIZ_TIME_DEFAULT)
    parser.add_argument("-ms", "--max_stream_time", help="max streaming time", type=int, default=MAX_STREAM_TIME_DEFAULT)
    parser.add_argument("-z", "--zoom_range", help="zooming range for zoomed viz stress", type=int, default=ZOOM_RANGE_DEFAULT)
    args = parser.parse_args()
    backend_args = {
        'url': args.url,
        'port': args.port,
        'ns': args.namespace,
    }
    if any([args.n_viewers, args.viz_list]):
        assert all([args.n_viewers, args.viz_list]) == True, "for viz stress, both viz_list and n_viewers should be specified"
    return args, backend_args


def start_streaming():
    p = Thread(target=streaming_proc)
    p.start()


def get_date_from_sample_name(fname):
    ptns = [
            '*%Y.%m.%d*%Hh%Mm%Ss*',
            '*%Y%m%d_%H%M_*',
            '*%Y%m%d_*',
           ]
    for ptn in ptns:
        matcher = datetime_glob.Matcher(pattern=ptn)
        dt = matcher.match(fname)
        if dt:
            break
    if dt is None:
        raise Exception(f"Error parsing sample name for date: {fname}")
    dt = dt.as_datetime()
    return '%.4d.%.2d.%.2d' %(dt.year, dt.month, dt.day)


def streaming_proc():
    # TODO: parallel streaming (with streamer.n_jobs > 1) 
    print(f"started streamer {current_thread().name}")
    i = 0
    while not shutdown_event.is_set():
        i += 1
        logging.info(f"({i}) Acquiring list of {len(stream_samples)} samples: begin " + 5*'<')
        for fname in stream_samples:
            # target zarr is constantly overwritten - remove prev.remnants of it
            target_fname = args.namespace + '_' + fname
            target_fname = os.path.join(args.target_data_pool_path, get_date_from_sample_name(fname), target_fname)
            shutil.rmtree(target_fname, ignore_errors=True)
            # (re)import raw sample
            raw_samples_data = [
                {'filename': fname, 'path': None},
            ]
            asyncio.run(
                client.emit_raw_import(
                raw_samples_data,
                request_id='raw_import',
                max_exec_time=args.max_stream_time)
            )
            client.assert_requests_ok(['raw_import',])
            logging.info(f'Acquired sample: {client.acquired_samples} - {current_thread().name}')
            time.sleep(2)
            # clean up the target zarr
            shutil.rmtree(target_fname, ignore_errors=True)
        logging.info(f"({i}) Acquiring list of {len(stream_samples)} samples: end " + 5*'>')
    asyncio.run( client.emit_stop_raw_import() )
    print(f"stopped streamer {current_thread().name}")


def  run_viewers(n_viewers, mz_range=None):
    for _ in range(n_viewers):
        v = Thread(target=viewer_proc, args=[mz_range,])
        v.start()


def get_t_range_max_from_zarr_name(fname):
    full_zarr_path = os.path.join(args.target_data_pool_path, get_date_from_sample_name(fname), fname)
    with open(os.path.join(full_zarr_path, '.props')) as f:
        props = json.load(f)
    return  int(props['length']) - 1


def viewer_proc(mz_range=None):
    global viz_request_ids
    zoom_token = 'zooming' if mz_range else ''
    print(f"started {zoom_token} viewer {current_thread().name}")
    request_ids = []
    for i, fname in enumerate(viz_samples):
        if shutdown_event.is_set():
            break
        t_range_max = get_t_range_max_from_zarr_name(fname)
        rq_suffix = client.set_viz_test_params(fname, t_range_max=t_range_max, max_exec_time=args.max_viz_time)
        request_id = f'{current_thread().name}:{i}_{rq_suffix}'
        request_ids.append(request_id)          # sync inside the thread
        # TODO: lock viz_request_ids for multi-thread sync?
        viz_request_ids.append(request_id)      # sync inside main if Ctrl+C
        t_start = time.time()
        asyncio.run(
            client.emit_visualize_range(
                        fname,
                        request_id=request_id,
                        mz_range=mz_range,
                        # viz_types=["spectrogram", "timeseries", "waterfall"],
                        viz_types=["spectrogram"],
            )
        )
        # alt: this sync is for sequential viewing
        client.assert_requests_ok(request_ids=[request_id])
        logging.info(f"   {fname} : {round(time.time()-t_start, 1)}")
    # # alt: this sync is for paraller viewing
    # client.assert_requests_ok(request_ids=request_ids)
    print(f"stopped {zoom_token} viewer {current_thread().name}")


def run_visualizations(mz_range=None):
    global viz_request_ids
    zoom_token = 'zooming' if mz_range else ''
    for i in range(args.n_viewers):
        logging.info(f"Running {i+1} {zoom_token} viewers: begin " + 10*'<')
        viz_request_ids = []
        client.viewed_samples = []
        run_viewers(n_viewers=i+1, mz_range=mz_range)
        time.sleep(1)
        client.assert_requests_ok(request_ids=viz_request_ids)
        # # alt: logging for parallel viewing
        # delim = '\n '
        # logging.info(f"Visualized samples:{delim}{delim.join([str(s) for s in client.viewed_samples])}")
        time.sleep(2)
        logging.info(f"Running {i+1} {zoom_token} viewers: end " + 10*'>')


def run_full_size_visualizations():
    run_visualizations()

def run_zoomed_visualizations():
    zoom_base = 200
    run_visualizations(mz_range=[zoom_base, zoom_base + args.zoom_range])


def run_until_complete():
    print('main started')
    if args.stream_list:
        start_streaming()
    while True:
        try:
            if args.viz_list:      # Run series of visualizations and quit
                run_full_size_visualizations()
                run_zoomed_visualizations()
                break
            elif args.stream_list:  # while streaming only, cycle till Ctrl+C to stop
                time.sleep(3)
            else:
                break
        except KeyboardInterrupt:
            logging.info('KeyboardInterrupt')
            break
        except Exception as e:
            logging.info(f"{e.__class__.__name__}({str(e)})")
            break
    client.shutdown_event.set()
    asyncio.run( client.emit_stop_raw_import() )
    asyncio.run( client.emit_stop_visualize_range(viz_request_ids) )
    print('main stopped')
    client.stop_client(f'TestClient finished')



def run():
    global args, client, shutdown_event, viz_samples, stream_samples
    args, backend_args = parse_args()

    if args.viz_list:
        with open(args.viz_list) as f:
            viz_samples = f.readlines()
    if args.stream_list:
        with open(args.stream_list) as f:
            stream_samples = f.readlines()

    client = start_test_client_as_daemon(**backend_args)
    shutdown_event = client.shutdown_event

    run_until_complete()


if __name__ == "__main__":
    run()