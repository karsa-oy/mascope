"""Python bindings to Tofwerk's TwTool DLL"""

import ctypes as ct
import os
import platform

import numpy as np
from numpy.ctypeslib import ndpointer

from mascope_tofwerk.runtime import runtime

toollib = None

config = runtime.config.tofwerk_dll
[libdir, libfile] = {
    "Linux": ["linux_x86_64", "libtwtool.so"],
    "Windows": ["windows_x64", "TwToolDll.dll"],
    "Darwin": ["macos_x86_64", "libtwtool.dylib"],  # broken?
}[
    (
        config  # use provided platform config
        if config != "Auto"  # unless its auto (the default)
        else platform.system()  # in which case infer platform
    )
]
libpath = runtime.path(
    "libraries",
    "tofwerk",
    "src",
    "mascope_tofwerk",
    "lib",
    "dlls",
    libdir,
    libfile,
)
runtime.logger.info(
    f"Loading Tofwerk TwTool DLL from mascope_tofwerk/lib/dlls/{libdir}/{libfile}"
)
if os.getenv("SKIP_TOFWERK_DLL"):
    runtime.logger.info("Skipping Tofwerk DLL loading in CI environment")
    toollib = None
else:
    toollib = ct.cdll.LoadLibrary(libpath)
    runtime.logger.info("Succesfully Loaded Tofwerk TwTool DLL")

if toollib is not None:
    tof2mass = toollib.TwTof2Mass if os.name == "posix" else toollib._TwTof2Mass

    def TwTof2Mass(tofSample, massCalibMode, p):
        tof2mass.restype = ct.c_double
        if isinstance(p, np.ndarray):
            tof2mass.argtypes = [ct.c_double, ct.c_int, ndpointer(np.float64)]
        else:
            tof2mass.argtypes = [ct.c_double, ct.c_int, ct.POINTER(ct.c_double)]
        return tof2mass(tofSample, massCalibMode, p)

    mass2tof = toollib.TwMass2Tof if os.name == "posix" else toollib._TwMass2Tof

    def TwMass2Tof(mass, massCalibMode, p):
        mass2tof.restype = ct.c_double
        if isinstance(p, np.ndarray):
            mass2tof.argtypes = [ct.c_double, ct.c_int, ndpointer(np.float64)]
        else:
            mass2tof.argtypes = [ct.c_double, ct.c_int, ct.POINTER(ct.c_double)]
        return mass2tof(mass, massCalibMode, p)

    translaterv = (
        toollib.TwTranslateReturnValue
        if os.name == "posix"
        else toollib._TwTranslateReturnValue
    )

    def TwTranslateReturnValue(ReturnValue):
        translaterv.argtypes = [ct.c_int]
        translaterv.restype = ct.c_char_p
        return translaterv(ReturnValue)

    fitsinglepeak = (
        toollib.TwFitSinglePeak if os.name == "posix" else toollib._TwFitSinglePeak
    )

    def TwFitSinglePeak(
        nbrDataPoints,
        yVals,
        xVals,
        peakType,
        blOffset,
        blSlope,
        amplitude,
        fwhmLo,
        fwhmHi,
        peakPos,
        mu,
    ):
        if isinstance(yVals, np.ndarray):
            fitsinglepeak.argtypes = [
                ct.c_int,
                ndpointer(np.float64, shape=nbrDataPoints),
                ndpointer(np.float64, shape=nbrDataPoints),
                ct.c_int,
                ndpointer(np.float64, shape=1),
                ndpointer(np.float64, shape=1),
                ndpointer(np.float64, shape=1),
                ndpointer(np.float64, shape=1),
                ndpointer(np.float64, shape=1),
                ndpointer(np.float64, shape=1),
                ndpointer(np.float64, shape=1),
            ]
        else:
            fitsinglepeak.argtypes = [
                ct.c_int,
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
                ct.c_int,
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
            ]
        return fitsinglepeak(
            nbrDataPoints,
            yVals,
            xVals,
            peakType,
            blOffset,
            blSlope,
            amplitude,
            fwhmLo,
            fwhmHi,
            peakPos,
            mu,
        )

    fitsinglepeak2 = (
        toollib.TwFitSinglePeak2 if os.name == "posix" else toollib._TwFitSinglePeak2
    )

    def TwFitSinglePeak2(nbrDataPoints, yVals, xVals, peakType, param):
        if isinstance(yVals, np.ndarray):
            fitsinglepeak2.argtypes = [
                ct.c_int,
                ndpointer(np.float64, shape=nbrDataPoints),
                ndpointer(np.float64, shape=nbrDataPoints),
                ct.c_int,
                ndpointer(np.float64, shape=7),
            ]
        else:
            fitsinglepeak2.argtypes = [
                ct.c_int,
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
                ct.c_int,
                ct.POINTER(ct.c_double),
            ]
        return fitsinglepeak2(nbrDataPoints, yVals, xVals, peakType, param)

    evalsinglepeak = (
        toollib.TwEvalSinglePeak if os.name == "posix" else toollib._TwEvalSinglePeak
    )

    def TwEvalSinglePeak(xVal, param):
        evalsinglepeak.restype = ct.c_double
        if isinstance(param, np.ndarray):
            evalsinglepeak.argtypes = [ct.c_double, ndpointer(np.float64, shape=7)]
        else:
            evalsinglepeak.argtypes = [ct.c_double, ct.POINTER(ct.c_double)]
        return evalsinglepeak(xVal, param)

    getmoleculemass = (
        toollib.TwGetMoleculeMass if os.name == "posix" else toollib._TwGetMoleculeMass
    )

    def TwGetMoleculeMass(molecule, mass):
        if isinstance(mass, np.ndarray):
            getmoleculemass.argtypes = [ct.c_char_p, ndpointer(np.float64, shape=1)]
        else:
            getmoleculemass.argtypes = [ct.c_char_p, ct.POINTER(ct.c_double)]
        return getmoleculemass(molecule, mass)

    multipeakfit = (
        toollib.TwMultiPeakFit if os.name == "posix" else toollib._TwMultiPeakFit
    )

    def TwMultiPeakFit(
        nbrDataPoints, dataX, dataY, nbrPeaks, mass, intensity, commonPar, options
    ):
        if isinstance(dataX, np.ndarray):
            multipeakfit.argtypes = [
                ct.c_int,
                ndpointer(np.float64, shape=nbrDataPoints),
                ndpointer(np.float64, shape=nbrDataPoints),
                ct.c_int,
                ndpointer(np.float64, shape=nbrPeaks),
                ndpointer(np.float64, shape=nbrPeaks),
                ndpointer(np.float64, shape=6),
                ct.c_int,
            ]
        else:
            multipeakfit.argtypes = [
                ct.c_int,
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
                ct.c_int,
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
                ct.c_int,
            ]
        return multipeakfit(
            nbrDataPoints, dataX, dataY, nbrPeaks, mass, intensity, commonPar, options
        )

    evalmultipeak = (
        toollib.TwEvalMultiPeak if os.name == "posix" else toollib._TwEvalMultiPeak
    )

    def TwEvalMultiPeak(x, nbrPeaks, mass, intensity, commonPar):
        evalmultipeak.restype = ct.c_double
        if isinstance(mass, np.ndarray):
            evalmultipeak.argtypes = [
                ct.c_double,
                ct.c_int,
                ndpointer(np.float64, shape=nbrPeaks),
                ndpointer(np.float64, shape=nbrPeaks),
                ndpointer(np.float64, shape=6),
            ]
        else:
            evalmultipeak.argtypes = [
                ct.c_double,
                ct.c_int,
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
            ]
        return evalmultipeak(x, nbrPeaks, mass, intensity, commonPar)

    fitresolution = (
        toollib.TwFitResolution if os.name == "posix" else toollib._TwFitResolution
    )

    def TwFitResolution(nbrPoints, mass, resolution, R0, m0, dm):
        if isinstance(mass, np.ndarray):
            fitresolution.argtypes = [
                ct.c_int,
                ndpointer(np.float64, shape=nbrPoints),
                ndpointer(np.float64, shape=nbrPoints),
                ndpointer(np.float64, shape=1),
                ndpointer(np.float64, shape=1),
                ndpointer(np.float64, shape=1),
            ]
        else:
            fitresolution.argtypes = [
                ct.c_int,
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
            ]
        return fitresolution(nbrPoints, mass, resolution, R0, m0, dm)

    evalresolution = (
        toollib.TwEvalResolution if os.name == "posix" else toollib._TwEvalResolution
    )

    def TwEvalResolution(R0, m0, dm, mass):
        evalresolution.restype = ct.c_double
        evalresolution.argtypes = [ct.c_double, ct.c_double, ct.c_double, ct.c_double]
        return evalresolution(R0, m0, dm, mass)

    # -------------------- Oskari added the stuff below -------------------------------
    masscalibrate = (
        toollib.TwMassCalibrate if os.name == "posix" else toollib._TwMassCalibrate
    )

    def TwMassCalibrate(
        massCalibMode, nbrPoints, mass, tof, weight, nbrParams, p, legacyA, legacyB
    ):
        if isinstance(mass, np.ndarray):
            masscalibrate.argtypes = [
                ct.c_int,
                ct.c_int,
                ndpointer(np.float64, shape=nbrPoints),
                ndpointer(np.float64, shape=nbrPoints),
                ndpointer(np.float64, shape=nbrPoints),
                ndpointer(int, shape=1),
                ndpointer(np.float64, shape=nbrParams[0]),
                ndpointer(np.float64, shape=1),
                ndpointer(np.float64, shape=1),
            ]
        else:
            masscalibrate.argtypes = [
                ct.c_int,
                ct.c_int,
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
                ct.c_int,
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
                ct.POINTER(ct.c_double),
            ]
        return masscalibrate(
            massCalibMode, nbrPoints, mass, tof, weight, nbrParams, p, legacyA, legacyB
        )

    getisotopepattern = (
        toollib.TwGetIsotopePattern
        if os.name == "posix"
        else toollib._TwGetIsotopePattern
    )

    def TwGetIsotopePattern(
        molecule, abundanceLimit, nbrIsotopes, isoMass, isoAbundance
    ):
        if isoMass is None and isoAbundance is None:
            getisotopepattern.argtypes = [
                ct.c_char_p,
                ct.c_double,
                ndpointer(int, shape=1),
                ct.c_void_p,
                ct.c_void_p,
            ]
        else:
            getisotopepattern.argtypes = [
                ct.c_char_p,
                ct.c_double,
                ndpointer(int, shape=1),
                ndpointer(np.float64),
                ndpointer(np.float64),
            ]
        return getisotopepattern(
            molecule, abundanceLimit, nbrIsotopes, isoMass, isoAbundance
        )

    decomposemass = (
        toollib.TwDecomposeMass if os.name == "posix" else toollib._TwDecomposeMass
    )

    def TwDecomposeMass(
        targetMass,
        tolerance,
        nbrAtoms,
        atomMass,
        atomLabel,
        nbrFilters,
        elementIndex1,
        elementIndex2,
        filterMinVal,
        filterMaxVal,
        nbrCompomers,
    ):
        decomposemass.argtypes = [
            ct.c_double,
            ct.c_double,
            ct.c_int,
            ndpointer(np.float64),
            ct.c_char_p,
            ct.c_int,
            ndpointer(int),
            ndpointer(int),
            ndpointer(np.float64),
            ndpointer(np.float64),
            ndpointer(int),
        ]
        return decomposemass(
            targetMass,
            tolerance,
            nbrAtoms,
            atomMass,
            atomLabel,
            nbrFilters,
            elementIndex1,
            elementIndex2,
            filterMinVal,
            filterMaxVal,
            nbrCompomers,
        )

    getcomposition = (
        toollib.TwGetComposition if os.name == "posix" else toollib._TwGetComposition
    )

    def TwGetComposition(index, sumFormula, sumFormulaLength, mass, massError):
        getcomposition.argtypes = [
            ct.c_int,
            ct.c_char_p,
            ndpointer(int),
            ndpointer(np.float64),
            ndpointer(np.float64),
        ]
        return getcomposition(index, sumFormula, sumFormulaLength, mass, massError)

else:
    # stub functions so init imports don't fail
    def TwMassCalibrate(*args, **kwargs):
        raise RuntimeError("Tofwerk DLL not available")

    def TwTof2Mass(*args, **kwargs):
        raise RuntimeError("Tofwerk DLL not available")

    def TwMass2Tof(*args, **kwargs):
        raise RuntimeError("Tofwerk DLL not available")
