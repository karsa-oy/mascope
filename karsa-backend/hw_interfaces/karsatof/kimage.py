# -*- coding: utf-8 -*-
"""Data visualization related functions and classes.

Created on Fri Mar  6 13:45:15 2020

@author: Oskari Kausiala
"""

import numpy as np
import pandas as pd
import xarray
import h5py
import warnings

from datetime import timedelta
from copy import copy, deepcopy
from concurrent.futures import Future
from concurrent.futures.process import ProcessPoolExecutor
from multiprocessing import Queue, Event
from threading import Thread
from queue import Empty

from PIL import Image
from io import BytesIO
from base64 import b64decode, b64encode

import datashader as ds
import datashader.transfer_functions as tf
from colorcet import fire

from karsatof.kutil import QueueSubscription

# JSON compatible template for plotly scatter trace
DEFAULT_TRACE = {'x': [],
                 'y': [],
                 'name': '',
                 'mode': 'lines',
                 'type': 'scattergl',
                 'line': {'color': '#fff'}, 
                 'visible': True, 
                 'hoverinfo': 'name,y'
                 }

def gen_timeseries_trace(data_xarray,
                         t_range=None,
                         mz_range=None):
    """Generate timeseries trace for certain time and mz ranges.
    All signals in the said mz range will be summed to make one trace.


    Parameters
    ----------
    data_xarray : DataArray
        Array with the data to visualize
    t_range : tuple, optional
        2-tuple with start time and end time of the desired time
        range (seconds), by default None. If None, full range will be used.
    mz_range : tuple, optional
        2-tuple with min m/z and max m/z of the desired mass
        range, by default None. If None, full range will be used.

    Returns
    -------
    dict
        JSON compatible plotly scatter trace where x = time
        and y = signal

    """

    if t_range is None:
        t_range = (data_xarray.time[0], data_xarray.time[-1])
    if mz_range is None:
        mz_range = (data_xarray.mz[0], data_xarray.mz[-1])
    sub_xarray = data_xarray.sel(mz=slice(mz_range[0],
                                          mz_range[1]),
                                 time=slice(t_range[0],
                                            t_range[1])
                                 )
    trace = deepcopy(DEFAULT_TRACE)
    trace.update({'x': np.array(sub_xarray.time).tolist(),
                  'y': np.array(sub_xarray.sum(dim='mz')).tolist()
                  }
                 )
    return trace

def gen_heatmap_image(data_xarray,
                      t_range=None,
                      mz_range=None,
                      img_width=None,
                      img_height=600
                      ):
    """Generate heatmap image to visualize spectra in 2D using datashader

    # TODO: At the moment ugly workarounds needed to generate 1 px wide heatmap
            slice. Raise an issue in datashader project?

    Parameters
    ----------
    data_xarray : DataArray
        Array with the data to visualize
    t_range : tuple, optional
        2-tuple with start time and end time of the desired time
        range (seconds), by default None. If None, full range will be used.
    mz_range : tuple, optional
        2-tuple with min m/z and max m/z of the desired mass
        range, by default None. If None, full range will be used.
    img_width : int, optional
        Image width (pixels), by default None. If None, data_xarray.shape[1]
        is used.
    img_height : int, optional
        Image height (pixels), by default 600

    Returns
    -------
    Image
        PIL Image containing the heatmap, time advances from
        left to right,  m/z from bottom to top.

    """

    # Ignore RuntimeWarning: "invalid value encountered in double_scalars
    # xres = (xcoords[-1] - xcoords[0]) / (w - 1)"
    warnings.filterwarnings("ignore", category=RuntimeWarning)

    if data_xarray.time.dtype == '<m8[ns]':
        # Convert timedelta to float
        data_xarray = data_xarray.assign_coords(
                {'time': [float(t.item()*1e-9) for t in data_xarray.time]}
                )

    if t_range is None:
        if data_xarray.time.shape:
            if img_width is None:
                img_width = len(data_xarray.time)
            t0 = data_xarray.time[0].item()
            t1 = data_xarray.time[-1].item()
            if t1 == t0:
                data_xarray = xarray.concat([data_xarray, data_xarray], dim='time')
                t1 += 1 # Arbitrary t1
        else:
            # Only one spectrum to visualize, need to expand array dimensions
            t0 = float(data_xarray.time)
            t1 = t0 + 1 # Arbitrary t1
            img_width = 1 # px
            data_xarray = data_xarray.expand_dims({'time': [t0]}, axis=1)
            # Make a spec of NaNs and concatenate to data_xarray
            expand_spec = np.empty(data_xarray.shape)
            expand_spec.fill(np.nan)
            expand_arr = xarray.DataArray(expand_spec,
                                          dims=data_xarray.dims,
                                          coords={'mz': data_xarray.mz,
                                                  'time': [t1]}
                                          )
            data_xarray = xarray.concat([data_xarray, expand_arr], dim='time')

        t_range = (t0, t1)

    if mz_range is None:
        mz0 = data_xarray.mz[0].item()
        mz1 = data_xarray.mz[-1].item()
        mz_range = (mz0, mz1)

    # Replace values < 0 with nan (not to be visualized, not to blow up the scale)
    data_xarray = data_xarray.where(data_xarray >= 0)
    
    # Check if only zeros in the range
    sum_signal = data_xarray.sel(time=slice(*t_range),
                                 mz=slice(*mz_range)
                                 ).sum().compute().item()
    if sum_signal == 0:
        # No need to compute, just return black
        img = Image.new('RGBA', (img_width, img_height), (0, 0, 0))
        return img

    cvs = ds.Canvas(x_range=t_range,
                    y_range=mz_range,
                    plot_height=img_height,
                    plot_width=img_width
                    )
    agg = cvs.quadmesh(data_xarray, x='time', y='mz')
    img = tf.shade(agg, cmap=fire)
    #img = tf.set_background(img, "black")
    return img.to_pil()

def hstack_imgs(slice_imgs):
    """Merge image slices horizontally into one image

    Assumes all images to be merged are of same height

    Parameters
    ----------
    slice_imgs : list
        List of slice Images to merge

    Returns
    -------
    PIL.Image
        merged image

    """

    # Calculate image width
    img_width = 0
    img_height = 0
    for img in slice_imgs:
        img_width += img.size[0]
        # Assume all slices have same height
        img_height = img.size[1]
    merge_img = Image.new('RGBA',
                          (img_width,
                           img_height)
                          )
    x = 0
    for img in slice_imgs:
        # Paste slice
        merge_img.paste(img, (x, 0), img)
        x += img.size[0]
    return merge_img



def gen_spec_stack_image(data_xarray,
                         t_range,
                         mz_range,
                         avg_s=0.0,
                         img_width=600,
                         img_height=1200):
    """Generate spec images and stack them

    Parameters
    ----------
    data_xarray : DataArray
        Array with the data to visualize
    t_range : tuple, optional
        2-tuple with start time and end time of the desired time
        range (seconds), by default None. If None, full range will be used.
    mz_range : tuple, optional
        2-tuple with min m/z and max m/z of the desired mass
        range, by default None. If None, full range will be used.
    avg_s : float, optional
        Length of data to be averaged per trace (seconds), by default 0.0.
        If <= data time resolution, one trace per spectrum will be generated.
    img_width : int, optional
        Image width (pixels), by default 600
    img_height : int, optional
        Image height (pixels), by default 1200

    Returns
    -------
    Image
        PIL Image containing the spec stack.

    """

    # Select subset of data within set ranges
    sub_xarray = data_xarray.sel(mz=slice(mz_range[0], mz_range[1]),
                                 time=slice(t_range[0], t_range[1])
                                 )

    # Convert time dimension to timedelta for resampling
    sub_xarray = sub_xarray.assign_coords(
                    {'time': [timedelta(seconds=t.item()) for t in sub_xarray.time]}
                    )

    # Check aceraging parameter
    if avg_s <= 0:
        # Set avg_s to data time resolution
        avg_s = (sub_xarray.time[1] - sub_xarray.time[0]).item() # ns
        avg_s *= 1e-9 # ns -> s

    # Resample to 'avg_s'
    sub_xarray = sub_xarray.resample(time='%.1fS' % avg_s).mean()

    # Generate trace per spectrum
    traces = []
    for spectrum in sub_xarray.transpose():
        imgi = gen_spec_image(spectrum,
                              y_range=None,
                              img_width=img_width,
                              img_height=200
                              )
        t = spectrum.time.data.item() * 1e-9
        traces.append({'t_range': [t, t],
                       'img': imgi
                       })
    
    # Stack images
    img = stack_spec_images(traces,
                            t_range=None,
                            n_traces=None,
                            img_width=img_width,
                            img_height=img_height)
    return img
        

def gen_spec_image(data_xarray,
                   y_range=None,
                   img_width=600,
                   img_height=200
                   ):
    """Function to generate single spec trace image using datashader.
    Signals in the input array will be flattened time-wise.

    TODO: Something need to be done
    with y scaling?

    Parameters
    ----------
    data_xarray : DataArray
        Array with the data to visualize
    y_range : tuple, optional
        2-tuple with signal range to be visualized, by default None.
        If None, range will be from 0 to max(signal).
    img_width : int, optional
        Image width (pixels), by default 600
    img_height : int, optional
        Image height (pixels), by default 200

    Returns
    -------
    Image
        PIL Image containing a trace for a single spectrum.

    """

    # Flatten
    if 'time' in data_xarray.dims:
        # Sum timewise to get y
        y = data_xarray.mean(dim='time')
    else:
        y = data_xarray.values

    if y_range is None:
        # Set y_range[1] to max of signal
        y_max = float( y.max() )
        y_range = (0, y_max)
    # Make sure yrange[1] not zero
    y1 = max(1e-5, y_range[1])
    y_range = (y_range[0], y1)

    # mz axis
    mz = data_xarray.mz.data
    # Generate image for single trace
    cvs = ds.Canvas(x_range=(mz[0], mz[-1]),
                    y_range=y_range,
                    plot_height=img_height,
                    plot_width=img_width
                    )
    data_df = pd.DataFrame({'mz': mz, 'y': y})
    agg = cvs.line(data_df, 'mz', 'y')
    img = tf.shade(agg, cmap='white')
    return img.to_pil()


def stack_spec_images(spec_traces,
                      t_range=None,
                      n_traces=None,
                      img_width=600,
                      img_height=1200):
    """Function to combine list of spec traces into a stack image.

    Horizontal axis is m/z, vertical axis is time.

    NOTE: Currently time axis is reversed!

    TODO: Need to figure out a way to make vertical axis somehow meaningful,
    maybe add some input parameters to enable more control

    Parameters
    ----------
    spec_traces : list
        List of dicts of spec traces. Each dict should be of the form:
        {'img': Image,  't_range': tuple}
    t_range : tuple, optional
        2-tuple with start time and end time of the desired time
        range (seconds), by default None. If None, all traces will be used.
    n_traces : int, optional
        Number of traces to divide the image canvas for, by default None.
        If None, inferred from the number of spec traces.
    img_width : int, optional
        Image width (pixels), by default 600
    img_height : int, optional
        Image height (pixels), by default 1200

    Returns
    -------
    Image
        PIL Image containing the spec stack.

    """
    
    # Initialize image
    stack_img = Image.new(
                    'RGBA',
                    (img_width, img_height)
                    )
    # Number of images to combine
    n_imgs = len(spec_traces)
    # Number of traces to make room for
    if n_traces is None:
        n_traces = n_imgs
    # No images
    if n_imgs == 0:
        return stack_img
    # Height of a single image
    spec_img_height = spec_traces[0].get('img').size[1]
    # Vertical offset between images to be stacked
    if n_traces == 1:
        offset = img_height-spec_img_height
        y_pos = offset
    else:
        offset = (img_height-spec_img_height) / (n_traces-1)
        y_pos = img_height-spec_img_height
    # Set indices in case there are more images 
    if t_range is None:
        # No time range specified
        i0 = 0
        i1 = i0 + min(n_traces, n_imgs)
    else:
        # Select traces in the requested time range
        i0 = None
        i1 = None
        for i, trace in enumerate(spec_traces):
            if (i0 is None and
                trace.get('t_range')[0] >= t_range[0]):
                i0 = i
            elif trace.get('t_range')[1] > t_range[1]:
                i1 = i
                break
        if i1 is None:
            i1 = len(spec_traces)
    # Loop through images in reversed order
    # to make newest one appear on the bottom
    for trace in list(reversed(spec_traces))[i0:i1]:
        img = trace.get('img')
        stack_img.paste(img, (0, int(y_pos)), img)
        y_pos -= offset
    return stack_img

def gen_ridge_traces(ridge_df, t=None, mz=None):
    """Generate Plotly traces for ridges

    Parameters
    ----------
    ridge_df : DataFrame
        DataFrame containing the ridges (generated by KOnlinePeakId)
    t : list, optional
        Time vector, by default None. If None, indices will be used
        instead of actual time.
    mz : list, optional
        m/z vector, by default None. If None, indices will be used
        instead of actual m/z.
    """

    global DEFAULT_TRACE # Trace template

    traces = []
    for _, row in ridge_df.iterrows():
        ridge = row.ridge
        if t is not None:
            x = [ t[i] for i in ridge[1] ]
        else:
            x = ridge[1]
        if mz is not None:
            y = [ mz[i] for i in ridge[0] ]
        else:
            y = ridge[0]
        ridge_trace = deepcopy(DEFAULT_TRACE)
        ridge_trace.update({'x': x, 'y': y, 'name': row.name})
        traces.append(ridge_trace)
    return traces

def convert_to_base64(img):
    """Convert PIL image to base64 png string

    Parameters
    ----------
    img : Image
        Input PIL Image

    Returns
    -------
    str
        Input image as base64 png string

    """

    b = BytesIO()
    img.save(b, format='png')
    return "data:image/png;base64,{0}".format(
        b64encode(b.getvalue()).decode('utf-8')
        )

def convert_base64_to_img(b64_img):
    """Convert base64 png string into PIL Image

    Parameters
    ----------
    b64_img : str
        base64 png string

    Returns
    -------
    PIL.Image
        Image object
    """

    str_img = b64decode( b64_img.split(',')[1] )
    b = BytesIO(str_img)
    img = Image.open(b)
    return img

def write_img_to_h5(filename, location, img):
    """Write an image to h5 file as an array of uint8

    Parameters
    ----------
    filename : str
        Full file path to write into
    location : str
        Dataset within the file to write the image into
    img : Image
        PIL Image to write to file
    
    """

    print('Writing image to : ' + location)
    with h5py.File(filename, 'r+') as h5f:
        if location in h5f:
            # Delete previous image if exists
            del(h5f[location])
        # Write image as an array to file
        img_arr = np.array(img)
        h5f.create_dataset(location,
                           data=img_arr
                           )
        # h5f.create_dataset(location,
        #                    np.shape(img),
        #                    h5py.h5t.STD_U8BE,
        #                    data=img
        #                    )

def read_img_from_h5(filename, location):
    """Read image from h5 file and return as PIL.Image

    Parameters
    ----------
    filename : str
        Full file path to read from
    location : str
        Dataset within the file to read the image from

    Returns
    -------
    Image
        PIL Image read from the file

    """

    with h5py.File(filename, 'r') as h5f:
        # Read image array from the file
        img_arr = h5f[location][()]
        # Convert to PIL.Image and return
        return Image.fromarray(img_arr)


class KHeatmapGenerator(Thread):
    """Heatmap generator thread which connects with KAcquisition to visualize
    the data stream. This thread is supposed to run always with acquisition
    to generate image of the data to be saved in the file.

    TODO: Cleaning up needed after recent modifications.
          Move writing to file away from here.


    Attributes
    ----------
    xarray : DataArray
        data_collector.xarray containing the raw data to visualize
    h5_write_lock : Lock
        Lock object to synchronize file access among threads
    queue_in : Queue
        Queue to synchronize visualization with acquisition
    queue_out : Queue
        Queue to put generated images into. NOTE: Not used atm
    img_height : int
        Image height (pixels)
    heatmap : dict
        Dictionary with the image and ranges to be consumed
        by DataVizService
    updated : Event
        'updated' is set by this thread each time the heatmap is updated.
        Consumer (e.g. DataVizService) should clear it when consuming to
        keep things synchronized.
    data_shape : tuple
        2-tuple with expected data shape, reset at the beginning of
        an acquisition
    coords : list
        [mz, time] coordinates of the data xarray
    """

    def __init__(self,
                 xarray,
                 sync_queue,
                #  h5_write_lock,
                 img_height=600
                 ):
        """Initialize self

        Parameters
        ----------
        xarray : xarray.DataArray
            DataArray with the data to visualize
        sync_queue : Queue
            Queue of speci, to synchronize visualization with acquisition
        h5_write_lock : Lock
            Lock object to synchronize file access among threads
        img_height : int, optional
            Image height (pixels), by default 600

        """

        #XXX Suppress annoying warnings
        import warnings
        warnings.filterwarnings('ignore')
        
        Thread.__init__(self)
        self.xarray = xarray
        # self.h5_write_lock = h5_write_lock
        self.queue_in = sync_queue
        self.img_height = img_height
        self.heatmap = {'mz_range': [],
                        't_range': [],
                        'img': []
                        }
        self.updated = Event()
    
    def init_acq(self):
        """Get data shape and coordinates for a new acquisition
        """

        self.updated.clear()
        t = self.xarray.time
        mz = self.xarray.mz
        self.data_shape = (len(mz), len(t))
        self.coords = [mz, t]

    
    def run(self):
        """Main loop

        The thread runs as long as 'data_collector' is running. It waits
        for acquisition, and then starts visualizing it as new data comes in.

        Raises
        ------
        Exception
            Exception is raised if there is a mismatch in indices,
            meaning that synchronization has failed for some reason.
            For debugging purposes.
        """

        while True:
            poisoned = False
            speci = -1
            try:
                speci = self.queue_in.get(timeout=.1)
            except Empty:
                continue

            if speci != -1:
                raise Exception('Something unexpected')

            print('KHeatmapGenerator initializing')
            self.init_acq()
            all_slices = []
            new_slices = []
            # Main loop, per acquisition
            while not poisoned:
                # Get from speci queue
                try:
                    data = self.queue_in.get(.1)
                except Empty:
                    continue
                if data is not None:
                    speci = data
                    print('Generating heatmap for speci: %s' %speci)
                    # Set mz range
                    mz0 = float(self.xarray.mz[0])
                    mz1 = float(self.xarray.mz[-1])
                    mz_range = (mz0, mz1)
                    # Set t range
                    t0 = float(self.xarray.time[speci])
                    t1 = float(t0 + np.diff(self.xarray.time)[0])
                    t_range = (t0, t1)
                    # Generate slice of the image from new data
                    heatmap_slice = gen_heatmap_image(
                            self.xarray,
                            t_range,
                            mz_range,
                            1, # width
                            self.img_height # height
                            )
                    all_slices.append(heatmap_slice)
                    # If previous update was not retrieved,
                    # combine current update with the previous
                    if self.updated.is_set():
                        t0 = self.heatmap.get('t_range')[0]
                        # Merge pending slices with the new one
                        new_slices.append(heatmap_slice)
                        heatmap_slice = merge_heatmap_slices(new_slices)
                    else:
                        # Reset pending slices
                        new_slices = [ heatmap_slice ]
                    self.heatmap.update(
                        {'mz_range': list(mz_range),
                         't_range': [t0, t1],
                         'img': convert_to_base64(
                                    heatmap_slice
                                    )
                         })
                    self.updated.set()
                else:
                    poisoned = True
                    break

            # Merge slices into one big image and write to file
            if len(all_slices) > 0:
                full_heatmap_img = merge_heatmap_slices(all_slices)
                print('KHeatmapGenerator file write disbled')
                # print('KHeatmapGenerator about to write into file')
                # self.h5_write_lock.acquire()
                # write_img_to_h5(filename, 
                #                 '/Karsa/heatmap',
                #                 full_heatmap_img
                #                 )
                # self.h5_write_lock.release()
                print('KHeatmapGenerator ready!')
 
        # Exit
        print('KHeatmapGenerator exiting')    
    
    
class KSpecImageGenerator(Thread):
    """Spectrum image generator thread which connects with KAcquisition
    to visualize the data stream. This thread is supposed to run always
    with acquisition to generate image of the data to be saved in the file.

    Attributes
    ----------
    xarray : DataArray
        data_collector.xarray containing the raw data to visualize
    queue_in : Queue
        Queue to synchronize visualization with acquisition
    avg_step : int, optional
        Flatten this many spectra into one trace, by default 1.
    queue_out : Queue
        Queue to put generated images into, to be consumed e.g.
        by KSpecStacker
    img_width : int, optional
        Image width (pixels), by default 600
    img_height : int, optional
        Image height (pixels), by default 200
    data_shape : tuple
        2-tuple with expected data shape, reset at the beginning of
        an acquisition
    coords : list
        [mz, time] coordinates of the data xarray
    """
    def __init__(self,
                 xarray,
                 sync_queue,
                 avg_step=1,
                 img_width=600,
                 img_height=200
                 ):

        Thread.__init__(self)
        self.xarray = xarray
        self.queue_in = sync_queue
        self.avg_step = avg_step
        self.queue_out = Queue()
        self.img_width = img_width
        self.img_height = img_height
        # spec_stack_img = Image.new('RGBA', (img_width, img_height))
        # self.spec_stack = {'mz_range': [0, 1],
        #                    't_range': [0, 1],
        #                    'img': convert_to_base64(spec_stack_img)
        #                    }
        # self.updated = Event()
      
    def init_acq(self):
        """
        Get data shape and coordinates for each acquisition
        """
        t = self.xarray.time
        mz = self.xarray.mz
        self.data_shape = (len(mz), len(t))
        self.coords = [mz, t]
    
    def run(self):
        """
        Run while KAcquisition runs
        """
        while True:
            poisoned = False
            avgi = -1
            speci = -1
            try:
                speci = self.queue_in.get(timeout=1)
            except Empty:
                continue
            if speci != -1:
                raise Exception('Something unexpected')
            print('KSpecImageGenerator initializing')
            self.init_acq()
            # Main loop, per acquisition
            while not poisoned:
                # spec_traces = []
                avg_speci = -1
                sub_t0 = None
                avgi += 1
                # Set avg (sub) indices
                x0 = avgi * self.avg_step
                if x0 >= len(self.coords[1]):
                    # Expecting poison pill
                    data = self.queue_in.get()
                    if data is None:
                        poisoned = True
                        break
                    else:
                        print('data: %s' %data)
                        print('avgi: %s' %avgi)
                        print('x0: %s' %x0)
                        raise Exception('Expected poison pill')
                x1 = x0 + self.avg_step
                # Make sure to not go out of bounds
                x1 = min(x1, len(self.coords[1])-1)
                # Sub loop, until avg_step is reached
                while avg_speci < self.avg_step-1:
                    try:
                        data = self.queue_in.get(.1)
                    except Empty:
                        continue
                    if data is not None:
                        speci = data
                        print('Generating spec trace for speci: %s' %speci)
                        avg_speci = speci - x0
                        # Check in case of skipped spectra
                        if avg_speci > self.avg_step - 1:
                            continue
                        # Set mz range
                        mz0 = self.xarray.mz[0].item()
                        mz1 = self.xarray.mz[-1].item()
                        mz_range = (mz0, mz1)
                        # Set t range
                        if sub_t0 is None:
                            # Store first time point in a variable
                            sub_t0 = self.xarray.time[x0].item()
                        if x0+avg_speci+1 < self.xarray.shape[1]:
                            # All but last point
                            sub_t1 = self.xarray.time[x0+avg_speci+1].item()
                                
                        else:
                            # The last point needs to be handled a bit differently
                            t1 = self.xarray.time[-1].item()
                            sub_t1 = t1 + np.diff(self.xarray.time)[0]
                        t_range = (sub_t0, sub_t1)
                        # Generate slice of the image from new data
                        spec_img = gen_spec_image(
                                        self.xarray,
                                        t_range,
                                        mz_range,
                                        None,
                                        self.img_width,
                                        self.img_height
                                        )
                        self.queue_out.put(
                                (t_range,
                                  mz_range,
                                  spec_img
                                  #convert_to_base64(spec_img)
                                  )
                                )
                        # if len(spec_traces)>0:
                        #     prev_t0 = spec_traces[-1].get('t_range')[0]
                        #     if prev_t0 == t_range[0]:
                        #         spec_traces.pop()
                                
                        # spec_traces.append(
                        #     {'mz_range': mz_range,
                        #      't_range': t_range,
                        #      'img': spec_img
                        #      })
                        # spec_stack_img = stack_spec_images(
                        #                   spec_traces,
                        #                   t_range=None #XXX
                        #                   )
                        # t0 = spec_traces[0].get('t_range')[0]
                        # t1 = t_range[1]
                        # self.spec_stack.update(
                        #     {'mz_range': list(mz_range),
                        #      't_range': [t0, t1],
                        #      'img': convert_to_base64(
                        #          #spec_img
                        #          spec_stack_img
                        #                  )
                        #      })
                        # self.updated.set()
                    else:
                        poisoned = True
                        break
            self.queue_out.put(None)
        # Exit
        self.queue_out.put(False)
        print('KSpecImageGenerator exiting')
        
        
class KSpecStacker(Thread):
    """Thread to consume spec traces generated by KSpecImageGenerator
    and stack them into one image "spec stack".

    TODO: Move writing to file away from here

    Attributes
    ----------
    xarray : DataArray
        data_collector.xarray containing the raw data to visualize
    queue_in : Queue
        Spec trace queue of KSpecImageGenerator
    h5_write_lock : Lock
            Lock object to synchronize file access among threads
    avg_step : int, optional
        KSpecImageGenerator averaging step, by default 1.
        Used to calculate expected number of traces.
    img_width : int, optional
        Image width (pixels), by default 600
    img_height : int, optional
        Image height (pixels), by default 1200
    spec_stack : dict
        Dictionary with the image and ranges to be consumed
        by DataVizService.
    updated : Event
        'updated' is set by this thread each time the spec stack is updated.
        Consumer (e.g. DataVizService) should clear it when consuming to
        keep things synchronized.
    """

    def __init__(self,
                 xarray,
                 spec_trace_queue,
                #  h5_write_lock,
                 avg_step=1,
                 img_width=600,
                 img_height=1200):
        """Initialize self

        Parameters
        ----------
        xarray : KAcquisition
            KAcquisition instance to synchronize with 
        spec_trace_queue : Queue
            Spec trace queue of KSpecImageGenerator
        h5_write_lock : Lock
            Lock object to synchronize file access among threads
        avg_step : int, optional
            KSpecImageGenerator averaging step, by default 1.
            Used to calculate expected number of traces.
        img_width : int, optional
            Image width (pixels), by default 600
        img_height : int, optional
            Image height (pixels), by default 1200

        """

        Thread.__init__(self)
        self.xarray = xarray
        self.queue_in = spec_trace_queue
        # self.h5_write_lock = h5_write_lock
        self.avg_step = avg_step
        self.img_width = img_width
        self.img_height = img_height
        self.spec_stack = {}
        self.updated = Event()
    
    def run(self):
        """Main loop

        The thread runs as long as it gets poisoned by KSpecImageGenerator.
        It gets single spectrum traces from the input queue and stacks them into
        one image, to be consumed e.g. by DataVizService. At the end of acquisition
        it writes the spec stack image into the acquired file.
        """

        poisoned = False
        # Main loop
        while not poisoned:
            # New acquisition, reset
            img = None # Last retrieved heatmap image
            prev_img = None # Last incomplete heatmap slice
            prev_t_range = (None, None) # Time range of last heatmap slice
            spec_traces = []
            ntraces = 0
            self.updated.clear()
            # Acquisition loop
            while True:
                # Get spec trace
                try:
                    data = self.queue_in.get(.1)
                except Empty:
                    continue
                if data:
                    if ntraces == 0:
                        # filename = copy(self.kacq.acquired_file)
                        ntraces = int(np.ceil(self.xarray.shape[1]/self.avg_step))
                    t_range, mz_range, img = data
                    data = {"img": img, 
                            "t_range": list(t_range), 
                            "mz_range": list(mz_range)
                            }
                    if prev_img is None:
                        # Received first image, initialize chart
                        pass
                    elif t_range[0] == prev_t_range[0]:
                        # Start time of new slice same as start time of previous
                        # => Slice still incomplete
                        # Pop the last incomplete slice if any
                        if len(spec_traces) > 0:
                            spec_traces.pop()
                    else:
                        # Start time of this image is different than previous
                        # => Previous slice is complete,
                        # img is the first image of new slice
                        pass
                    # Append retrieved data
                    spec_traces.append(data)
                    # Store last image and start time
                    prev_img = img
                    prev_t_range = t_range
                    # Generate stack image
                    spec_stack_img = stack_spec_images(
                                         spec_traces,
                                         t_range=None,
                                         n_traces=ntraces,
                                         img_width=self.img_width,
                                         img_height=self.img_height
                                         )
                    t0 = spec_traces[0].get('t_range')[0]
                    t1 = self.xarray.time[-1].item()
                    self.spec_stack.update(
                        {'mz_range': list(mz_range),
                         't_range': [t0, t1],
                         'img': convert_to_base64(
                                     spec_stack_img
                                     )
                         })
                    self.updated.set()
                elif data is None:
                    # Got None (poison pill)
                    if (len(spec_traces) == 0 or 
                        spec_traces[-1] != img):
                        # Got None before the current slice was complete
                        if data is not None:
                            # Append incomplete slice to the list
                            spec_traces.append(data)    
                    # Write to file
                    print('KSpecStacker file write disabled')
                    # print('KSpecStacker about to write into file')
                    # self.h5_write_lock.acquire()
                    # for i, trace in enumerate(spec_traces):
                    #     t_range = trace.get('t_range')
                    #     mz_range = trace.get('mz_range')
                    #     img = trace.get('img')
                    #     write_img_to_h5(filename,
                    #                     '/Karsa/spectra/%s' %i,
                    #                     img
                    #                     )
                    # write_img_to_h5(filename,
                    #                 '/Karsa/spec_stack',
                    #                 spec_stack_img
                    #                 )
                    # self.h5_write_lock.release()
                    print('KSpecStacker ready!')
                    break
                else:
                    # Got False => spec generator exiting
                    poisoned = True
                    break
        print("KSpecStacker exiting")