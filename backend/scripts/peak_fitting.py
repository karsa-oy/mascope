# -*- coding: utf-8 -*-
"""
Created on Mon Oct 31 16:32:19 2022

@author: Oskari Kausiala
"""

import numpy as np

from backend.lib.file import load_file

#%%
filename = r'C:\Data\instrument\KLTOF2\2021.08.19\KLTOF2_Comissioning-C4Q-xxx-L_2021.08.19-17h59m16s'
filename = r'C:\Data\instrument\unknown\2021.08.19\unknown_Comissioning-C4Q-xxx-L_2021.08.19-17h59m16s'
cache_item = load_file(filename, vars=['signal'])

mz = cache_item.mz
spec = cache_item.signal.sum(dim='time')

#%%
from backend.lib.signal.peak import load_peakshape_mat

peakshape_file = r'C:\Users\Oskari Kausiala\Documents\Repositories\labbis\parameters\peakShapes\peakshape.mat'    
peakshape = load_peakshape_mat(peakshape_file)

p1 = 0.000125
p2 = 0.002545
R = lambda m: m / (p1 * m + p2)

# R = lambda m: R0 - (R0 / (1 + np.exp((m - m0) / dm)))


#%%
from backend.lib.signal.peak import fit_n_peaks

# def calculate_peak_areas(x, y, peakshape, peaks):
#     kernel = np.zeros((len(x), len(peaks)))
#     for i, (pos, hei, res) in enumerate(peaks):
#         peak_kernel = gen_peak(x, pos, hei, res, peakshape)
#         kernel[:, i] = peak_kernel
#         print(sum(peak_kernel))
#     _, _, _, peak_areas = np.linalg.lstsq(kernel, y, rcond=None)
#     peaks = [
#         (pos, hei, res, peak_areas[i])
#         for i, (pos, hei, res) in enumerate(peaks)
#         ]
#     return peaks

um = 125
dmz = .3
umz = mz.sel(mz=slice(um-dmz, um+dmz)).compute().values
uspec = spec.sel(mz=slice(um-dmz, um+dmz)).compute().values

#%%
fit, peaks = fit_n_peaks(
    umz,
    uspec,
    peakshape,
    R,
    max_n_peaks=10,
    threshold=.9
    )

#%
from backend.lib.signal.peak import gen_peak
from matplotlib import pyplot as plt

plt.plot(umz, uspec)
for pos, hei, res, area in peaks:
    plt.plot(umz, gen_peak(umz, pos, hei, res, peakshape))
plt.plot(umz, fit.residual)

print(list(zip(*peaks))[3])

#%%
from backend.lib.signal.peak import fwhm_to_sigma, gen_gaussian_peakshape, gen_peak
from matplotlib import pyplot as plt
from scipy.interpolate import interp1d

min_signal_norm = 5000
good_residual_to_signal_ratio = 0.1
dmz = .3

gaussian_peakshape = gen_gaussian_peakshape()

all_peaks = []
peakshapes = []
ps_x = np.linspace(-30, 30, 601)

for um in range(32, 600):
    print(um)
    fit = None
    peaks = []
    umz = mz.sel(mz=slice(um-dmz, um+dmz)).compute().values
    uspec = spec.sel(mz=slice(um-dmz, um+dmz)).compute().values
    
    uspec_norm = np.linalg.norm(uspec)
    
    if uspec_norm > min_signal_norm:
        fit, peaks = fit_n_peaks(
            umz,
            uspec,
            gaussian_peakshape,
            R,
            max_n_peaks=1,
            threshold=.5,
            fit_pos=False,
            fit_res=True,
            )
        residual_norm = np.linalg.norm(fit.residual)
        good_fit = residual_norm / uspec_norm <= good_residual_to_signal_ratio
        
        all_peaks.extend(peaks)
    if len(peaks) == 1 and good_fit:
        print("good fit")
        # peakshape
        peak = peaks[0]
        fwhm = peak[0] / peak[2]
        if fwhm > 0.1:
            continue
        sigma = fwhm_to_sigma(fwhm)
        uspec_n = uspec / max(uspec)
        mz_n = umz - peak[0]
        ind = np.logical_and(mz_n >= -dmz, mz_n <= +dmz)
        ps_x_u = mz_n[ind] / sigma
        ps_y_u = interp1d(ps_x_u, uspec_n[ind], bounds_error=False, fill_value=0)(ps_x)
        peakshapes.append(ps_y_u)
peakshapes = np.array(peakshapes)
plt.plot(peakshapes.T)
plt.plot(np.median(peakshapes, axis=0))
#%%
    plt.figure()
    plt.plot(umz, uspec)
    for pos, hei, res, area in peaks:
        plt.plot(umz, gen_peak(umz, pos, hei, res, peakshape))
    if fit:
        plt.plot(umz, fit.residual)
        
#%%
max_res = max(list(zip(*all_peaks))[2])
ok_peaks = [peak for peak in all_peaks if peak[2] >= 0.5*max_res]

plt.scatter(list(zip(*ok_peaks))[0], list(zip(*ok_peaks))[2])