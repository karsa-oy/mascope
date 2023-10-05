"""Python bindings to Tofwerk's TofDaq DLL
"""

import ctypes as ct
import os
import platform
import sys
from enum import Enum

import numpy as np
from numpy.ctypeslib import ndpointer

libname = {"win32": "TofDaqDll.dll"}
libpath = ""
if platform.architecture() == ("32bit", "WindowsPE"):
    libpath = "windows_x86"
elif platform.architecture() == ("64bit", "WindowsPE"):
    libpath = "windows_x64"
else:
    raise EnvironmentError(str(platform.architecture()))

tofdaqdll = ct.cdll.LoadLibrary(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "dlls",
        libpath,
        libname[sys.platform],
    )
)


_double_array = ndpointer(dtype=np.float64, flags="CONTIGUOUS")
_float_array = ndpointer(dtype=np.float32, flags="CONTIGUOUS")


class TSharedMemoryDesc(ct.Structure):
    _fields_ = [
        ("nbrSamples", ct.c_int),
        ("nbrRawSamples", ct.c_int),
        ("nbrPeaks", ct.c_int),
        ("nbrWaveforms", ct.c_int),
        ("nbrSegments", ct.c_int),
        ("nbrBlocks", ct.c_int),
        ("nbrMemories", ct.c_int),
        ("nbrBufs", ct.c_int),
        ("nbrWrites", ct.c_int),
        ("nbrRuns", ct.c_int),
        ("iWaveform", ct.c_int),
        ("iSegment", ct.c_int),
        ("iBlock", ct.c_int),
        ("iMemory", ct.c_int),
        ("iBuf", ct.c_int),
        ("iWrite", ct.c_int),
        ("iRun", ct.c_int),
        ("totalBufsRecorded", ct.c_int),
        ("totalBufsProcessed", ct.c_int),
        ("totalBufsWritten", ct.c_int),
        ("overallBufsProcessed", ct.c_int),
        ("totalNbrMemories", ct.c_int),
        ("totalMemoriesProcessed", ct.c_int),
        ("rawDataRecordedBuf1", ct.c_uint),
        ("rawDataRecordedBuf2", ct.c_uint),
        ("rawDataLastElementInBuffer1", ct.c_uint),
        ("rawDataLastElementInBuffer2", ct.c_uint),
        ("rawDataProcessedBuf1", ct.c_uint),
        ("rawDataProcessedBuf2", ct.c_uint),
        ("rawDataWrittenBuf1", ct.c_uint),
        ("rawDataWrittenBuf2", ct.c_uint),
        ("sampleInterval", ct.c_float),
        ("tofPeriod", ct.c_int),
        ("nbrCubes", ct.c_int),
        ("blockPeriod", ct.c_longlong),
        ("blockPulseDelay", ct.c_longlong),
        ("blockDelay", ct.c_longlong),
        ("singleIonSignal", ct.c_float),
        ("singleIonSignal2", ct.c_float),
        ("massCalibMode", ct.c_int),
        ("massCalibMode2", ct.c_int),
        ("nbrMassCalibParams", ct.c_int),
        ("nbrMassCalibParams2", ct.c_int),
        ("p", ct.c_double * 16),
        ("p2", ct.c_double * 16),
        ("R0", ct.c_float),
        ("dm", ct.c_float),
        ("m0", ct.c_float),
        ("secondTof", ct.c_bool),
        ("chIniFileName", ct.c_char * 256),
        ("currentDataFileName", ct.c_char * 256),
        ("segIlf", ct.c_ubyte),
        ("iCube", ct.c_ushort),
        ("daqMode", ct.c_int),
        ("acquisitionMode", ct.c_int),
        ("combineMode", ct.c_int),
        ("recalibFreq", ct.c_int),
        ("acquisitionLogText", ct.c_char * 256),
        ("acquisitionLogTime", ct.c_ulonglong),
        ("timeZero", ct.c_ulonglong),
        ("externalLock", ct.c_void_p),
        ("processingLevel", ct.c_uint),
        ("attributeType", ct.c_int),
        ("attributeObject", ct.c_char * 256),
        ("attributeName", ct.c_char * 128),
        ("attributeInt", ct.c_int),
        ("attributeDouble", ct.c_double),
        ("enableVarNbrMemories", ct.c_int),
        ("nbrSteps", ct.c_int),
        ("currentStepAtBuf", ct.c_int),
        ("nbrMemoriesForCurrentStep", ct.c_int),
    ]


class TPeakPar(ct.Structure):
    _fields_ = [
        ("label", ct.c_char * 64),
        ("mass", ct.c_float),
        ("loMass", ct.c_float),
        ("hiMass", ct.c_float),
    ]


class TSharedMemoryPointer(ct.Structure):
    _fields_ = [
        ("sumSpectrum", ct.POINTER(ct.c_double)),
        ("sumSpectrum2", ct.POINTER(ct.c_double)),
        ("tofData", ct.POINTER(ct.POINTER(ct.c_float))),
        ("tofData2", ct.POINTER(ct.POINTER(ct.c_float))),
        ("peakData", ct.POINTER(ct.c_float)),
        ("peakData2", ct.POINTER(ct.c_float)),
        ("timing", ct.POINTER(ct.c_double)),
        ("rawData32Ch1", ct.POINTER(ct.c_uint32)),
        ("rawData16Ch1", ct.POINTER(ct.c_uint16)),
        ("rawData8Ch1", ct.POINTER(ct.c_int8)),
        ("rawData32Ch2", ct.POINTER(ct.c_uint32)),
        ("rawData16Ch2", ct.POINTER(ct.c_uint16)),
        ("rawData8Ch2", ct.POINTER(ct.c_int8)),
    ]


class TwRetVal(Enum):
    TwDaqRecNotRunning = 0
    TwAcquisitionActive = 1
    TwNoActiveAcquisition = 2
    TwFileNotFound = 3
    TwSuccess = 4
    TwError = 5
    TwOutOfBounds = 6
    TwNoData = 7
    TwTimeout = 8
    TwValueAdjusted = 9
    TwInvalidParameter = 10
    TwInvalidValue = 11
    TwAborted = 12


# --------------------- CONTROL FUNCTIONS ---------------------------------------
def TwInitializeDll():
    return ct.cdll.tofdaqdll._TwInitializeDll()


def TwCleanupDll():
    ct.cdll.tofdaqdll._TwCleanupDll()


def TwGetDllVersion():
    ct.cdll.tofdaqdll._TwGetDllVersion.restype = ct.c_double
    return ct.cdll.tofdaqdll._TwGetDllVersion()


def TwTofDaqRunning():
    ct.cdll.tofdaqdll._TwTofDaqRunning.restype = ct.c_bool
    return ct.cdll.tofdaqdll._TwTofDaqRunning()


def TwDaqActive():
    ct.cdll.tofdaqdll._TwDaqActive.restype = ct.c_bool
    return ct.cdll.tofdaqdll._TwDaqActive()


def TwStartAcquisition():
    return ct.cdll.tofdaqdll._TwStartAcquisition()


def TwStopAcquisition():
    return ct.cdll.tofdaqdll._TwStopAcquisition()


def TwContinueAcquisition():
    return ct.cdll.tofdaqdll._TwContinueAcquisition()


def TwManualContinueNeeded():
    if ct.cdll.tofdaqdll._TwManualContinueNeeded():
        return True
    else:
        return False


def TwCloseTofDaqRec():
    return ct.cdll.tofdaqdll._TwCloseTofDaqRec()


def TwLockBuf(timeout, bufToLock):
    ct.cdll.tofdaqdll._TwLockBuf.argtypes = [ct.c_int, ct.c_int]
    return ct.cdll.tofdaqdll._TwLockBuf(timeout, bufToLock)


def TwUnLockBuf(bufToUnlock):
    ct.cdll.tofdaqdll._TwUnLockBuf.argtypes = [ct.c_int]
    return ct.cdll.tofdaqdll._TwUnLockBuf(bufToUnlock)


def TwIssueDio4Pulse(delay, width):
    ct.cdll.tofdaqdll._TwIssueDio4Pulse.argtypes = [ct.c_int, ct.c_int]
    return ct.cdll.tofdaqdll._TwIssueDio4Pulse(delay, width)


def TwSetDio4State(state):
    ct.cdll.tofdaqdll._TwSetDio4State.argtypes = [ct.c_int]
    return ct.cdll.tofdaqdll._TwSetDio4State(state)


def TwOnDemandMassCalibration(action):
    ct.cdll.tofdaqdll._TwSetDio4State.argtypes = [ct.c_int]
    return ct.cdll.tofdaqdll._TwOnDemandMassCalibration(action)


# ----------------------- CONFIGURATION FUNCTIONS -------------------------------


def TwShowConfigWindow(configWindowIndex):
    return ct.cdll.tofdaqdll._TwShowConfigWindow(configWindowIndex)


def TwLoadIniFile(iniFilename):
    ct.cdll.tofdaqdll._TwLoadIniFile.argtypes = [ct.c_char_p]
    return ct.cdll.tofdaqdll._TwLoadIniFile(iniFilename)


def TwSaveIniFile(iniFilename):
    ct.cdll.tofdaqdll._TwLoadIniFile.argtypes = [ct.c_char_p]
    return ct.cdll.tofdaqdll._TwSaveIniFile(iniFilename)


def TwGetDaqParameter(Parameter):
    ct.cdll.tofdaqdll._TwGetDaqParameter.argtypes = [ct.c_char_p]
    ct.cdll.tofdaqdll._TwGetDaqParameter.restype = ct.c_char_p
    return ct.cdll.tofdaqdll._TwGetDaqParameter(Parameter)


def TwGetDaqParameterInt(Parameter):
    ct.cdll.tofdaqdll._TwGetDaqParameterInt.argtypes = [ct.c_char_p]
    ct.cdll.tofdaqdll._TwGetDaqParameterInt.restype = ct.c_int
    return int(ct.cdll.tofdaqdll._TwGetDaqParameterInt(Parameter))


def TwGetDaqParameterBool(Parameter):
    ct.cdll.tofdaqdll._TwGetDaqParameterBool.argtypes = [ct.c_char_p]
    ct.cdll.tofdaqdll._TwGetDaqParameterBool.restype = ct.c_bool
    return ct.cdll.tofdaqdll._TwGetDaqParameterBool(Parameter)


def TwGetDaqParameterFloat(Parameter):
    ct.cdll.tofdaqdll._TwGetDaqParameterFloat.argtypes = [ct.c_char_p]
    ct.cdll.tofdaqdll._TwGetDaqParameterFloat.restype = ct.c_float
    return float(ct.cdll.tofdaqdll._TwGetDaqParameterFloat(Parameter))


def TwGetDaqParameterInt64(Parameter):
    ct.cdll.tofdaqdll._TwGetDaqParameterInt64.argtypes = [ct.c_char_p]
    ct.cdll.tofdaqdll._TwGetDaqParameterInt64.restype = ct.c_int64
    return int(ct.cdll.tofdaqdll._TwGetDaqParameterInt64(Parameter))


def TwGetDaqParameterDouble(Parameter):
    ct.cdll.tofdaqdll._TwGetDaqParameterFloat.argtypes = [ct.c_char_p]
    ct.cdll.tofdaqdll._TwGetDaqParameterFloat.restype = ct.c_double
    return float(ct.cdll.tofdaqdll._TwGetDaqParameterDouble(Parameter))


def TwGetDaqParameterIntRef(Parameter, pValue):
    ct.cdll.tofdaqdll._TwGetDaqParameterInt.argtypes = [
        ct.c_char_p,
        ndpointer(np.int32, shape=1),
    ]
    return ct.cdll.tofdaqdll._TwGetDaqParameterIntRef(Parameter, pValue)


# Here a byte has to be used since there are no numpy bool arrays
def TwGetDaqParameterBoolRef(Parameter, pValue):
    ct.cdll.tofdaqdll._TwGetDaqParameterBoolRef.argtypes = [
        ct.c_char_p,
        ndpointer(c_bool, shape=1),
    ]
    return ct.cdll.tofdaqdll._TwGetDaqParameterBoolRef(Parameter, pValue)


def TwGetDaqParameterFloatRef(Parameter, pValue):
    ct.cdll.tofdaqdll._TwGetDaqParameterFloatRef.argtypes = [
        ct.c_char_p,
        ndpointer(np.float32, shape=1),
    ]
    return ct.cdll.tofdaqdll._TwGetDaqParameterFloatRef(Parameter, pValue)


def TwGetDaqParameterInt64Ref(Parameter, pValue):
    ct.cdll.tofdaqdll._TwGetDaqParameterInt64.argtypes = [
        ct.c_char_p,
        ndpointer(np.int64, shape=1),
    ]
    return ct.cdll.tofdaqdll._TwGetDaqParameterInt64Ref(Parameter, pValue)


def TwGetDaqParameterDoubleRef(Parameter, pValue):
    ct.cdll.tofdaqdll._TwGetDaqParameterDoubleRef.argtypes = [
        ct.c_char_p,
        ndpointer(np.float64, shape=1),
    ]
    return ct.cdll.tofdaqdll._TwGetDaqParameterDoubleRef(Parameter, pValue)


# This function is a bit complicated to use. It needs a numpy array of size 256 np.uint8.
# One then have to parse this manually looking for the null.
# Consult numpy.ndarray.tostring function for a hint to get started
def TwGetDaqParameterStringRef(Parameter, pValue):
    if isinstance(pValue, ct.c_char_p):
        ct.cdll.tofdaqdll._TwGetDaqParameterStringRef.argtypes = [
            ct.c_char_p,
            ct.c_char_p,
        ]
        return ct.cdll.tofdaqdll._TwGetDaqParameterStringRef(Parameter, pValue)
    else:
        ct.cdll.tofdaqdll._TwGetDaqParameterStringRef.argtypes = [
            ct.c_char_p,
            ndpointer(np.uint8, shape=256),
        ]
        return ct.cdll.tofdaqdll._TwGetDaqParameterStringRef(Parameter, pValue)


def TwSetDaqParameter(Parameter, Value):
    ct.cdll.tofdaqdll._TwSetDaqParameter.argtypes = [ct.c_char_p, ct.c_char_p]
    return ct.cdll.tofdaqdll._TwSetDaqParameter(Parameter, Value)


def TwSetDaqParameterInt(Parameter, Value):
    ct.cdll.tofdaqdll._TwSetDaqParameterInt.argtypes = [ct.c_char_p, ct.c_int]
    return ct.cdll.tofdaqdll._TwSetDaqParameterInt(Parameter, Value)


def TwSetDaqParameterBool(Parameter, Value):
    ct.cdll.tofdaqdll._TwSetDaqParameterBool.argtypes = [ct.c_char_p, ct.c_bool]
    return ct.cdll.tofdaqdll._TwSetDaqParameterBool(Parameter, Value)


def TwSetDaqParameterFloat(Parameter, Value):
    ct.cdll.tofdaqdll._TwSetDaqParameterFloat.argtypes = [ct.c_char_p, ct.c_float]
    return ct.cdll.tofdaqdll._TwSetDaqParameterFloat(Parameter, Value)


def TwSetDaqParameterInt64(Parameter, Value):
    ct.cdll.tofdaqdll._TwSetDaqParameterInt64.argtypes = [ct.c_char_p, ct.c_int64]
    return ct.cdll.tofdaqdll._TwSetDaqParameterInt64(Parameter, Value)


def TwSetDaqParameterDouble(Parameter, Value):
    ct.cdll.tofdaqdll._TwSetDaqParameterDouble.argtypes = [ct.c_char_p, ct.c_double]
    return ct.cdll.tofdaqdll._TwSetDaqParameterDouble(Parameter, Value)


def TwConfigVarNbrMemories(Enable, StepAtBuf, NbrMemoriesForStep):
    if len(StepAtBuf) != len(NbrMemoriesForStep):
        return TwError
    int_array_type = ct.c_int * len(StepAtBuf)
    Sarray = int_array_type(*StepAtBuf)
    Marray = int_array_type(*NbrMemoriesForStep)
    ct.cdll.tofdaqdll._TwConfigVarNbrMemories.argtypes = [
        ct.c_int,
        ct.c_int,
        int_array_type,
        int_array_type,
    ]
    return ct.cdll.tofdaqdll._TwConfigVarNbrMemories(
        Enable, len(StepAtBuf), Sarray, Marray
    )


def TwSetMassCalib(mode, nbrParams, p, nbrPoints, mass, tof, weight):
    ct.cdll.tofdaqdll._TwSetMassCalib.argtypes = [
        ct.c_int,
        ct.c_int,
        ndpointer(np.float64),
        ct.c_int,
        ndpointer(np.float64),
        ndpointer(np.float64),
        ndpointer(np.float64),
    ]
    return ct.cdll.tofdaqdll._TwSetMassCalib(
        mode, nbrParams, p, nbrPoints, mass, tof, weight
    )


# ---------------------------- DATA ACCESS FUNCTIONS ----------------------------


def TwGetDescriptor(ShMemDescriptor):
    ct.cdll.tofdaqdll._TwGetDescriptor.argtypes = [ct.POINTER(TSharedMemoryDesc)]
    return ct.cdll.tofdaqdll._TwGetDescriptor(ct.pointer(ShMemDescriptor))


# If PeakPar is None, a new TPeakPar is allocated, filled and returned
def TwGetPeakParameters(PeakIndex, PeakPar=None):
    if PeakPar != None:
        return ct.cdll.tofdaqdll._TwGetPeakParameters(ct.pointer(PeakPar), PeakIndex)
    else:
        tempPeakPar = TPeakPar()
        tempRv = ct.cdll.tofdaqdll._TwGetPeakParameters(pointer(tempPeakPar), PeakIndex)
        if TwTranslateReturnValue(tempRv) == "Success":
            return (
                tempPeakPar.label,
                tempPeakPar.mass,
                tempPeakPar.loMass,
                tempPeakPar.hiMass,
            )
        else:
            return tempRv


def TwGetSharedMemory(ShMem, keepMapped):
    ct.cdll.tofdaqdll._TwGetSharedMemory.argtypes = [
        ct.POINTER(TSharedMemoryPointer),
        ct.c_bool,
    ]
    return ct.cdll.tofdaqdll._TwGetSharedMemory(ct.pointer(ShMem), keepMapped)


def TwReleaseSharedMemory():
    return ct.cdll.tofdaqdll._TwReleaseSharedMemory()


def TwWaitForNewData(Timeout, ShMemDescriptor, ShMem, WaitForEventReset):
    if ShMem == None:
        ct.cdll.tofdaqdll._TwWaitForNewData.argtypes = [
            ct.c_int,
            ct.c_void_p,
            ct.POINTER(TSharedMemoryPointer),
            ct.c_bool,
        ]
        return ct.cdll.tofdaqdll._TwWaitForNewData(
            Timeout, ct.pointer(ShMemDescriptor), None, WaitForEventReset
        )
    else:
        ct.cdll.tofdaqdll._TwWaitForNewData.argtypes = [
            ct.c_int,
            ct.POINTER(TSharedMemoryDesc),
            ct.POINTER(TSharedMemoryPointer),
            ct.c_bool,
        ]
        return ct.cdll.tofdaqdll._TwWaitForNewData(
            Timeout, ct.pointer(ShMemDescriptor), ct.pointer(ShMem), WaitForEventReset
        )


def TwWaitForEndOfAcquisition(timeout):
    ct.cdll.tofdaqdll._TwWaitForEndOfAcquisition.argtypes = [ct.c_int]
    return ct.cdll.tofdaqdll._TwWaitForEndOfAcquisition(timeout)


def TwGetMassCalib(mode, nbrParams, p, nbrPoints, mass, tof, weight):
    ct.cdll.tofdaqdll._TwGetMassCalib.argtypes = [
        ndpointer(int, shape=1),
        ndpointer(int),
        _double_array,
        ndpointer(int, shape=1),
        _double_array,
        _double_array,
        _double_array,
    ]
    return ct.cdll.tofdaqdll._TwGetMassCalib(
        mode, nbrParams, p, nbrPoints, mass, tof, weight
    )


def TwGetSumSpectrumFromShMem(spectrum, normalize):
    ct.cdll.tofdaqdll._TwGetSumSpectrumFromShMem.argtypes = [_double_array, ct.c_byte]
    return ct.cdll.tofdaqdll._TwGetSumSpectrumFromShMem(spectrum, normalize)


def TwGetTofSpectrumFromShMem(
    spectrum, segmentIndex, segmentEndIndex, bufIndex, normalize
):
    ct.cdll.tofdaqdll._TwGetTofSpectrumFromShMem.argtypes = [
        _float_array,
        ct.c_int,
        ct.c_int,
        ct.c_int,
        ct.c_byte,
    ]
    return ct.cdll.tofdaqdll._TwGetTofSpectrumFromShMem(
        spectrum, segmentIndex, segmentEndIndex, bufIndex, normalize
    )


def TwGetSpecXaxisFromShMem(specAxis, axisType, unitLabel):
    ct.cdll.tofdaqdll._TwGetSpecXaxisFromShMem.argtypes = [
        _double_array,
        ct.c_int,
        ct.POINTER(ct.c_char),
    ]
    return ct.cdll.tofdaqdll._TwGetSpecXaxisFromShMem(specAxis, axisType, unitLabel)


def TwGetStickSpectrumFromShMem(
    spectrum, masses, segmentIndex, segmentEndIndex, bufIndex
):
    if masses == None:
        ct.cdll.tofdaqdll._TwGetStickSpectrumFromShMem.argtypes = [
            _float_array,
            ct.c_void_p,
            ct.c_int,
            ct.c_int,
            ct.c_int,
        ]
    else:
        ct.cdll.tofdaqdll._TwGetStickSpectrumFromShMem.argtypes = [
            _float_array,
            _float_array,
            ct.c_int,
            ct.c_int,
            ct.c_int,
        ]
    return ct.cdll.tofdaqdll._TwGetStickSpectrumFromShMem(
        spectrum, masses, segmentIndex, segmentEndIndex, bufIndex
    )


def TwGetSegmentProfileFromShMem(segmentProfile, peakIndex, bufIndex):
    ct.cdll.tofdaqdll._TwGetSegmentProfileFromShMem.argtypes = [
        _float_array,
        ct.c_int,
        ct.c_int,
    ]
    return ct.cdll.tofdaqdll._TwGetSegmentProfileFromShMem(
        segmentProfile, peakIndex, bufIndex
    )


def TwGetBufTimeFromShMem(bufTime, bufIndex, writeIndex):
    ct.cdll.tofdaqdll._TwGetBufTimeFromShMem.argtypes = [
        _double_array,
        ct.c_int,
        ct.c_int,
    ]
    return ct.cdll.tofdaqdll._TwGetBufTimeFromShMem(bufTime, bufIndex, writeIndex)


# ------------------- DATA STORAGE FUNCTIONS -----------------------------------
def TwAddLogEntry(logEntry, logEntryTime):
    ct.cdll.tofdaqdll._TwAddLogEntry.argtypes = [ct.c_char_p, ct.c_uint64]
    return ct.cdll.tofdaqdll._TwAddLogEntry(logEntry, logEntryTime)


def TwAddAttributeInt(objName, attributeName, value):
    ct.cdll.tofdaqdll._TwAddAttributeInt.argtypes = [ct.c_char_p, ct.c_char_p, ct.c_int]
    return ct.cdll.tofdaqdll._TwAddAttributeInt(objName, attributeName, value)


def TwAddAttributeDouble(objName, attributeName, value):
    ct.cdll.tofdaqdll._TwAddAttributeDouble.argtypes = [
        ct.c_char_p,
        ct.c_char_p,
        ct.c_double,
    ]
    return ct.cdll.tofdaqdll._TwAddAttributeDouble(objName, attributeName, value)


def TwAddAttributeString(objName, attributeName, value):
    ct.cdll.tofdaqdll._TwAddAttributeString.argtypes = [
        ct.c_char_p,
        ct.c_char_p,
        ct.c_char_p,
    ]
    return ct.cdll.tofdaqdll._TwAddAttributeString(objName, attributeName, value)


def TwAddUserData(location, nbrElements, elementDescription, data):
    ct.cdll.tofdaqdll._TwAddUserData.argtypes = [
        ct.c_char_p,
        ct.c_int,
        ct.c_char_p,
        _double_array,
    ]
    return ct.cdll.tofdaqdll._TwAddUserData(
        location, nbrElements, elementDescription, data
    )


def TwRegisterUserDataBuf(location, nbrElements, elementDescription, compressionLevel):
    ct.cdll.tofdaqdll._TwRegisterUserDataBuf.argtypes = [
        ct.c_char_p,
        ct.c_int,
        ct.c_char_p,
        ct.c_int,
    ]
    return ct.cdll.tofdaqdll._TwRegisterUserDataBuf(
        location, nbrElements, elementDescription, compressionLevel
    )


# def TwRegisterUserDataBufPy(location, elementDescription, compressionLevel):
#    if elementDescription != None:
#        descBuffer = create_string_buffer(len(elementDescription)*256)
#        for index in range(len(elementDescription)):
#            tempBuffer = create_string_buffer(elementDescription[index])
#            memmove(addressof(descBuffer)+index*256, addressof(tempBuffer), 256)
#    else:
#        descBuffer = None
#    return TwRegisterUserDataBuf(location, len(elementDescription), descBuffer, compressionLevel)


def TwRegisterUserDataWrite(
    location, nbrElements, elementDescription, compressionLevel
):
    ct.cdll.tofdaqdll._TwRegisterUserDataWrite.argtypes = [
        ct.c_char_p,
        ct.c_int,
        ct.c_char_p,
        ct.c_int,
    ]
    return ct.cdll.tofdaqdll._TwRegisterUserDataWrite(
        location, nbrElements, elementDescription, compressionLevel
    )


# def TwRegisterUserDataWritePy(location, elementDescription, compressionLevel):
#    if elementDescription != None:
#        descBuffer = create_string_buffer(len(elementDescription)*256)
#        for index in range(len(elementDescription)):
#            tempBuffer = create_string_buffer(elementDescription[index])
#            memmove(addressof(descBuffer)+index*256, addressof(tempBuffer), 256)
#    else:
#        descBuffer = None
#    return TwRegisterUserDataWrite(location, len(elementDescription), descBuffer, compressionLevel)


def TwUnregisterUserData(location):
    ct.cdll.tofdaqdll._TwUnregisterUserData.argtypes = [ct.c_char_p]
    return ct.cdll.tofdaqdll._TwUnregisterUserData(location)


def TwUpdateUserData(location, nbrElements, data):
    ct.cdll.tofdaqdll._TwUpdateUserData.argtypes = [
        ct.c_char_p,
        ct.c_int,
        _double_array,
    ]
    return ct.cdll.tofdaqdll._TwUpdateUserData(location, nbrElements, data)


# def TwUpdateUserDataPy(location, data):
#    dataBuffer = (c_double*len(data))()
#    for elementIndex in range(len(data)):
#        dataBuffer[elementIndex] = data[elementIndex]
#    return TwUpdateUserData(location, len(data), dataBuffer)
#
#
def TwReadRegUserData(location, nbrElements, data):
    ct.cdll.tofdaqdll._TwReadRegUserData.argtypes = [
        ct.c_char_p,
        ct.c_int,
        _double_array,
    ]
    return ct.cdll.tofdaqdll._TwReadRegUserData(location, nbrElements, data)


# ------------------------ TPS REMOTE CONTROL FUNCTIONS ------------------------


def TwTpsConnect():
    return ct.cdll.tofdaqdll._TwTpsConnect()


def TwTpsConnect2(ip, type):
    ct.cdll.tofdaqdll._TwTpsConnect2.argtypes = [ct.c_char_p, ct.c_int]
    return ct.cdll.tofdaqdll._TwTpsConnect2(ip, type)


def TwTpsDisconnect():
    return ct.cdll.tofdaqdll._TwTpsDisconnect()


def TwTpsGetMonitorValue(moduleCode, value):
    ct.cdll.tofdaqdll._TwTpsGetMonitorValue.argtypes = [
        ct.c_int,
        ndpointer(np.float64, shape=1),
    ]
    return ct.cdll.tofdaqdll._TwTpsGetMonitorValue(moduleCode, value)


def TwTpsGetTargetValue(moduleCode, value):
    ct.cdll.tofdaqdll._TwTpsGetTargetValue.argtypes = [
        ct.c_int,
        ndpointer(np.float64, shape=1),
    ]
    return ct.cdll.tofdaqdll._TwTpsGetTargetValue(moduleCode, value)


def TwTpsGetLastSetValue(moduleCode, value):
    ct.cdll.tofdaqdll._TwTpsGetLastSetValue.argtypes = [
        ct.c_int,
        ndpointer(np.float64, shape=1),
    ]
    return ct.cdll.tofdaqdll._TwTpsGetLastSetValue(moduleCode, value)


def TwTpsSetTargetValue(moduleCode, value):
    ct.cdll.tofdaqdll._TwTpsSetTargetValue.argtypes = [ct.c_int, ct.c_double]
    return ct.cdll.tofdaqdll._TwTpsSetTargetValue(moduleCode, value)


def TwTpsGetNbrModules(nbrModules):
    ct.cdll.tofdaqdll._TwTpsGetNbrModules.argtypes = [ndpointer(np.int32, shape=1)]
    return ct.cdll.tofdaqdll._TwTpsGetNbrModules(nbrModules)


def TwTpsGetModuleCodes(moduleCodeBuffer, bufferLength):
    ct.cdll.tofdaqdll._TwTpsGetModuleCodes.argtypes = [ndpointer(np.int32), ct.c_int]
    return ct.cdll.tofdaqdll._TwTpsGetModuleCodes(moduleCodeBuffer, bufferLength)


def TwTpsInitialize():
    ct.cdll.tofdaqdll._TwTpsInitialize.argtypes = []
    return ct.cdll.tofdaqdll._TwTpsInitialize()


def TwTpsSetAllVoltages():
    return ct.cdll.tofdaqdll._TwTpsSetAllVoltages()


def TwTpsShutdown():
    ct.cdll.tofdaqdll._TwTpsShutdown.argtypes = []
    return ct.cdll.tofdaqdll._TwTpsShutdown()


def TwTpsGetStatus(status):
    ct.cdll.tofdaqdll._TwTpsGetStatus.argtypes = [ndpointer(np.int32, shape=1)]
    return ct.cdll.tofdaqdll._TwTpsGetStatus(status)


def TwTpsLoadSetFile(setFile):
    ct.cdll.tofdaqdll._TwTpsLoadSetFile.argtypes = [ct.c_char_p]
    return ct.cdll.tofdaqdll._TwTpsLoadSetFile(setFile)


def TwTpsSaveSetFile(setFile):
    ct.cdll.tofdaqdll._TwTpsSaveSetFile.argtypes = [ct.c_char_p]
    return ct.cdll.tofdaqdll._TwTpsSaveSetFile(setFile)


# --------- Oskari added below ----------


def TwGetRegUserDataSources(arrayLength, location, nbrElements, typeint):
    argtypes = [
        ndpointer(int, shape=1),
        ct.c_char_p,
        ndpointer(int, shape=1),
        ndpointer(int, shape=1),
    ]
    if location is None:
        argtypes[1] = ct.c_void_p
    if nbrElements is None:
        argtypes[2] = ct.c_void_p
    if typeint is None:
        argtypes[3] = ct.c_void_p
    ct.cdll.tofdaqdll._TwGetRegUserDataSources.argtypes = argtypes
    return ct.cdll.tofdaqdll._TwGetRegUserDataSources(
        arrayLength, location, nbrElements, typeint
    )


def TwGetRegUserDataDesc(location, nbrElements, elementDescription):
    if elementDescription is None:
        ct.cdll.tofdaqdll._TwGetRegUserDataDesc.argtypes = [
            ct.c_char_p,
            ndpointer(int, shape=1),
            ct.c_void_p,
        ]
    else:
        ct.cdll.tofdaqdll._TwGetRegUserDataDesc.argtypes = [
            ct.c_char_p,
            ndpointer(int, shape=1),
            ct.c_char_p,
        ]
    return ct.cdll.tofdaqdll._TwGetRegUserDataDesc(
        location, nbrElements, elementDescription
    )


def TwQueryRegUserDataSize(location, nbrElements):
    ct.cdll.tofdaqdll._TwQueryRegUserDataSize.argtypes = [
        ct.c_char_p,
        ndpointer(int, shape=1),
    ]
    return ct.cdll.tofdaqdll._TwQueryRegUserDataSize(location, nbrElements)


def TwSetTimeout(timeout):
    ct.cdll.tofdaqdll._TwSetTimeout.argtypes = [ct.c_int]
    return ct.cdll.tofdaqdll._TwSetTimeout(timeout)
