# -*- coding: utf-8 -*-
"""
Created on Mon Dec  2 14:34:17 2019

@author: Oskari Kausiala
"""
import clr
import ctypes
import numpy as np

clr.AddReference('System.Runtime.InteropServices')
from System.Runtime.InteropServices import GCHandle, GCHandleType

def net2np_array(netarray):
    """ Given a CLR 'System.Array' returns a 'numpy.ndarray'. See _MAP_NET_NP for
    the mapping of CLR types to Numpy dtypes.
    """
    _MAP_NET_NP = {
        'Single' : np.dtype('float32'),
        'Double' : np.dtype('float64'),
        'SByte'  : np.dtype('int8'),
        'Int16'  : np.dtype('int16'),
        'Int32'  : np.dtype('int32'),
        'Int64'  : np.dtype('int64'),
        'Byte'   : np.dtype('uint8'),
        'UInt16' : np.dtype('uint16'),
        'UInt32' : np.dtype('uint32'),
        'UInt64' : np.dtype('uint64'),
        'Boolean': np.dtype('bool'),
    }
    dims = np.empty(netarray.Rank, dtype=int)
    for I in range(netarray.Rank):
        dims[I] = netarray.GetLength(I)
    nettype = netarray.GetType().GetElementType().Name    
    try:
        nparray = np.empty(dims, order='C', dtype=_MAP_NET_NP[nettype])
    except KeyError:
        raise NotImplementedError("as_nparray does not yet support System type {}".format(nettype) )
    try: # Memmove
        sourceHandle = GCHandle.Alloc(netarray, GCHandleType.Pinned)
        sourcePtr = sourceHandle.AddrOfPinnedObject().ToInt64()
        destPtr = nparray.__array_interface__['data'][0]
        ctypes.memmove(destPtr, sourcePtr, nparray.nbytes)
    finally:
        if sourceHandle.IsAllocated: sourceHandle.Free()
    return nparray