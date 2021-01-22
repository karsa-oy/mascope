import sys
import getopt
import asyncio
import socketio
import numpy as np

import aioconsole

from threading import Thread
from multiprocessing import (Barrier,
                             Event,
                             Queue,
                             RawArray,
                             Value,
                             cpu_count)
from queue import Empty

from karsalib import BaseClientNamespace
from karsatof.kfeeder import KFeeder, FeederProcessor
from karsatof.kworker import KEncoder
from karsatof.kcollector import KCollector
from karsatof.kutil import (read_peaklist,
                            peaklist_to_df,
                            load_peak_dict,
                            )


class SignalProcessorNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to Router """

    rooms = ['acquisition_coordinates',
             'acquired_spectrum',
             'acquisition_finished'
             ]
    
    async def on_acquisition_coordinates(self, data):
        """Initialize FeederProcessor with m/z axis

        Parameters
        ----------
        data : dict
            keys: 'mz' and 'time'
        """

        global u_list
        global feeder
        global collector

        mz = np.frombuffer( data.get('mz'), dtype=np.float32 )
        feeder.preprocessor.fit(mz, u_list)
        #collector.processor.fit(feeder.preprocessor.borders)


    async def on_acquired_spectrum(self, data):
        """Receive spectrum from TOFService

        Parameters
        ----------
        data : dict
            keys: 'i' and 'spec'
        """

        global feeder

        i = data.get('i')
        self.log(i)
        spec = np.frombuffer(data.get('spec'), dtype=np.float32)
        feeder.queue_in.put((i, spec))
        
    async def on_acquisition_finished(self, data):
        """Acquisition finished, feed poison pill to KFeeder        
        """
        
        global feeder
        feeder.queue_in.put(None)


async def emit_client_notification(name, value, **kwarg):
    global root_ns
    await root_ns.emit_client_notification(name, value, **kwarg)


def parse_cmd_args():
    """Parse command line arguments
    
    Allowed command line arguments
    ------------------------------
    --n_jobs : int
        Number of worker proceses to spawn
    """
    
    opts, _ = getopt.getopt(
                    sys.argv[1:],
                    [],
                    ['n_jobs=']
                    )
    for opt, arg in opts:
        if opt=='--n_jobs':
            try:
                global n_jobs
                n_jobs = int(arg)
            except:
                print('Invalid command line argument: %s=%s' %(opt, arg))
        else:
            print('Invalid command line argument: %s=%s' %(opt, arg))


async def init_service(url):
    
    global sio
    global root_ns
    
    while True:
        try:
            print('Connecting to Router...')
            await sio.connect(url, namespaces=['/',])
            break
        except Exception as e:
            print('Failed: %s' %e)

async def initialize_feeder():
    global feeder
    global process_q
    
    feeder = KFeeder(queue_out=process_q,
                     # barrier=Barrier(2)
                     )
    feeder.start()

async def initialize_encoders(process_q,
                              results_q,
                              n_jobs=cpu_count(),
                              alpha=Value('d', 1e-3),
                              error_log=False
                              ):
    """Initialize KEncoder processes

    Parameters
    ----------
    process_q : Queue 
        Queue for segments to be processed
    code_q : Queue
        Queue for KEncoder results
    n_jobs : int, optional
        Number of processes to initialize, by default the number
        of available CPU cores as returned by multiprocessing.cpu_count()
    alpha : multiprocessing.Value
        SparseCoder regularization parameter
    error_log : bool, optional
        Log KEncoder errors to txt files, by default False

    Returns
    -------
    encoders : list of KEncoder
        KEncoder process instances
    active_events : list of Event
        List of Event objects, one per KEncoder indicating whether
        they are currently processing an acquisition.
    """
    
    global encoders
    global encoder_active_events
    global D_file    
    
    print("Initializing workers...")
    
    # Load peak dictionary
    D = load_peak_dict(D_file) # scipy.sparse.csr_matrix
    # Make a RawArray of the dictionary D so that encoders can
    # access it without the need to copy whole dictionary for
    # each process
    D_data = RawArray('d', D.data)
    D_indices = RawArray('i', D.indices)
    D_indptr = RawArray('i', D.indptr)
    
    # Initialize n_jobs KEncoders    
    if n_jobs == -1:
        n_jobs = cpu_count()
    for _ in range(n_jobs):
        encoder_active = Event()
        # KEncoder process
        enc = KEncoder(alpha,
                       process_q,
                       results_q,
                       encoder_active,
                       D.shape,
                       D_data,
                       D_indices,   
                       D_indptr,
                       error_log=error_log
                       )
        encoders.append(enc)
        encoder_active_events.append(encoder_active)
    # Start encoders
    for i, enc in enumerate(encoders):
        print("Spawning worker %s/%s" %((i+1), n_jobs))
        enc.start()
        

async def initialize_collector():
    global collector
    global results_q
    
    collector = KCollector(results_q)
    collector.start()


async def run_service():
    global n_jobs
    global process_q
    global results_q
    
    await initialize_feeder()
    await initialize_collector()
    await init_service('http://localhost:5010')
    await initialize_encoders(process_q, results_q, n_jobs)
    await main()
    await kill_service()


async def kill_service():
    """Kill service
    

    Returns
    -------
    None.

    """
    global sio
    global feeder
    global encoders
    global process_q
    global results_q
    
    print("Terminating the service...")
    
    await sio.disconnect()
        
    if feeder.is_alive():
        feeder.queue_in.put(False)
        
    # Give some time to die
    await asyncio.sleep(1)
        
    any_process_alive = True
    while any_process_alive:
        # If there is still tasks in queue (other than poison pill),
        # force kill
        if process_q.qsize() > 1:
            [ worker.terminate() for worker in encoders ]
            
        # Poison pill should be left after the last worker spinning out
        elif process_q.qsize() == 1:
            try:
                # Clear poison pill left by last worker
                process_q.get_nowait()
            except Empty:
                # Workers still doing something
                continue
            
        # Something unexpected has happened, queue is empty
        else:
            # Force kill workers
            [ worker.terminate() for worker in encoders ]
            
        # Clear and join queues
        while process_q.qsize() > 0:
            process_q.get_nowait()
        process_q.close()
        process_q.join_thread()
        
        while results_q.qsize() > 0:
            try:
                results_q.get_nowait()
            except Empty:
                await asyncio.sleep(.1)
                
        results_q.close()
        results_q.join_thread()
        
        # Check if any processes are still alive (should not be)
        is_alive = [ worker.is_alive() for worker in encoders ]
        any_process_alive = np.array(is_alive).any()


async def main():
    """Main loop
    

    Returns
    -------
    None.

    """

    print("SignalProcessorService running")

    await aioconsole.ainput("Hit enter to kill me")

    # global results_q
    # global sio
    
    # while True:
    #     try:
    #         data = results_q.get_nowait()
    #     except Empty:
    #         await asyncio.sleep(.1)
    #         continue
    #     # Received results
    #     if data:
    #         # self.processor.transform(data)
    #         specis = data.get('specis')
    #         u = data.get('u')
    #         # snos = data.get('snos').astype(np.float32).tobytes()
    #         # spec = data.get('spec').astype(np.float32).tobytes()
    #         # approx = data.get('approx').astype(np.float32).tobytes()
    #         # code = data.get('code').astype(np.float32).tobytes()
    #         # peaks = data.get('peaks')
    #         await emit_client_notification('processed_segment',
    #                                        {'specis': specis,
    #                                         'u': u,
    #                                         #'snos': snos,
    #                                         #'spec': spec,
    #                                         #'approx': approx,
    #                                         #'code': code,
    #                                         #'peaks': peaks
    #                                         },
    #                                        no_data_logging=True
    #                                        )
    #     # Received poison pill
    #     else:
    #         # Got None
    #         if data is None:
    #             # TODO: Currently None should never be received
    #             pass
    #         else:
    #             # TODO: Currently False is never received
    #             break

                
                
u_list = []
u_list = range(200, 220)
# peaklist = '.\\resources\\xplpar.db'
D_file = '.\\py_code\\resources\\test.h5'

feeder = None
forwarder = None
collector = None
n_jobs = cpu_count()
encoders = [] # Processes
encoder_active_events = [] # Process active 
process_q = Queue()
results_q = Queue()


if __name__=='__main__':
    parse_cmd_args()        
    
    sio = socketio.AsyncClient()
    sio.register_namespace(SignalProcessorNamespace('/'))
    root_ns = sio.namespace_handlers['/']
        
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_service())