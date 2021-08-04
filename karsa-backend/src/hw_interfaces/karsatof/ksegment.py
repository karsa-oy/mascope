# -*- coding: utf-8 -*-
"""
Created on Wed Dec 11 15:22:29 2019

@author: Oskari Kausiala
"""

import numpy as np

from scipy.stats import mode

from karsalib.struct import ExtendableDataArray, IncrementalCOO
from .kcode import find_extrema

class KSegmentSequence():
    """Class representing a sequence of "codes" for a spectral segment.

    The segment sequence is appendable, and each time a new column of code
    is added, its local maxima are sought and connected with existing ridges
    (or if not found, new ridges are initiated). The ridges fulfilling certain
    criteria are considered to represent peaks in the spectra.

    Ridge detection related functions adapted from:
    https://github.com/scipy/scipy/blob/v1.5.2/scipy/signal/_peak_finding.py

    TODO: !!! Effect of 'max_seq_len' is not properly tested !!!

    Attributes
    ----------
    borders : tuple
        Sample number range of the segment
    snos : array
        Sample number vector of the segment
    max_distance : int
        Maximum distance in sample numbers between consecutive ridge points.
    gap_thresh : int
        Maximum gap allowed within a ridge.
    min_len : int
        Minimum ridge length for it to be considered a valid peak
    max_seq_len : int
        Maximum length of the sequence, needed for continuous operation.
    index : list
        List of spectrum indices
    code : array
        Code array
    ridge_lines : list
        List of ridges

    """

    def __init__(self,
                 borders,
                 max_seq_len=np.inf,
                 gap_thresh=1,
                 max_distance=1,
                 min_len=3):
        """Initialize self

        Parameters
        ----------
        borders : tuple
            Sample number range of the segment
        max_seq_len : int, optional
            Maximum length of the sequence, needed for continuous operation, 
            by default np.inf.
        gap_thresh : int, optional
            [description], by default 1.
        max_distance : int, optional
            Peak maximum distance in sample numbers between consecutive
            ridge points, by default 1.
        min_len : int, optional
            Minimum ridge length for it to be considered a valid peak,
            by default 3.
        """

        # Parameters
        self.max_distance = max_distance # Max distance (snos) between ridge points
        self.gap_thresh = gap_thresh # Maximum gap allowed within a ridge
        self.min_len = min_len # Minimum ridge length for peak detection
        self.max_seq_len = max_seq_len # Maximum length of the sequence
        
        # Data
        # self.borders = borders # (s0, s1)
        self.snos = np.arange(borders[0], borders[1])
        self.index = [] # speci
        self.partspec = ExtendableDataArray()
        self.code = IncrementalCOO(dtype=np.float32)
        self.ridge_lines = []

    def append(self, specis, new_spec, new_approx, new_code, new_peaks):
        """Add new column of data (code) to the sequence, find code maxima
        and extend/append ridges.

        Parameters
        ----------
        i : list
            List of spectrum indices (speci)
        code_col : array
            Code vector (from KEncoder)
        """

        self.index.extend(specis)

        # Extend ridge lines
        self.ridge_lines = self.extend_ridges(specis, new_peaks)
        
        if self.code.shape[0]==0:
            self.code = new_code.reshape((-1, 1))
        elif self.code.shape[1] < self.max_seq_len:
            # Append sequence
            self.code = np.hstack((self.code, new_code.reshape((-1, 1))))
        else:
            # Sequence has reached maximum length, roll new column in
            #TODO: Not properly tested
            self.index.pop(0)
            self.code = np.roll(self.code, 1, axis=1)
            self.code[:, -1] = new_code
    
    def extend_ridges(self, i, new_peaks):
        """Extend ridges with new peaks. If there is an existing ridge line
        within the 'max_distance' to connect to, do so. Otherwise start a
        new one. Removes ridge lines with gap number greater than 'gap_thresh'.

        Parameters
        ----------
        i : int
            Index (speci)
        code_col_extrema : array
            Local extrema in the code

        Returns
        -------
        list
            New ridge lines
        """

        if len(new_peaks) == 0:
            # No peaks, increase gap number in all existing ridge lines
            for line in self.ridge_lines:
                line[3] += 1
            return self.ridge_lines

        if len(self.ridge_lines) == 0:
            # Initialize ridge lines
            #Each ridge line is a 4-tuple:
            #sample number, spec index, peak height, Gap number
            ridge_lines = [ [[i],
                             [x],
                             [y],
                             0
                             ] for x, y in new_peaks
                            ]
            return ridge_lines
        # Extend existing ridge lines
        ridge_lines = self.ridge_lines
        #Increment gap number of each line,
        #set it to zero later if appropriate
        for line in ridge_lines:
            line[3] += 1
            if line[3] > self.gap_thresh:
                print('gap: %s' %line[3])
        # Loop through new peaks
        # Attempt to connect them with existing ridge lines.
        prev_peaks_x = np.array([line[1][-1] for line in ridge_lines])
        for peak_x, peak_y in new_peaks:
            line = None
            if len(prev_peaks_x) > 0:
                # Distances to existing ridges
                diffs = np.abs(peak_x - prev_peaks_x)
                closest = np.argmin(diffs)
                if diffs[closest] <= self.max_distance:
                    # Found matching ridge
                    line = ridge_lines[closest]
            if line is not None:
                # Extend new peak to the found ridge
                line[0].append(i)
                line[1].append(peak_x)
                line[2].append(peak_y)
                line[3] = 0
            else:
                # No existing ridge found within max_distance.
                # Start a new ridge
                new_line = [[i],
                            [peak_x],
                            [peak_y],
                            0
                            ]
                ridge_lines.append(new_line)
        #Remove the ridge lines with gap_number too high
        for ind in range(len(ridge_lines) - 1, -1, -1):
            line = ridge_lines[ind]
            if line[3] > self.gap_thresh:
                print('gap: %s, delete' %line[3])
                del ridge_lines[ind]

        return ridge_lines
        
    def filter_ridges(self, min_len):
        """Return ridges with minimum length of 'min_len'

        Parameters
        ----------
        min_len : int
            Minimum length of ridge line to return.

        Returns
        -------
        list
            Filtered ridge lines
        """

        if min_len is None:
            min_len = self.min_len
        good_ridges = []
        for rdg in self.ridge_lines:
            if len(rdg[0]) >= min_len:
                good_ridges.append(rdg)
        return good_ridges
        
    def get_peaks(self, min_ridge_len=None):
        """Get peak positions and heights, as inferred from the ridges.
        Filters ridge lines based on 'min_ridge_len', and returns the
        mode of their position (sample number) and sum of their height.

        TODO: This is a rather rudimentary way to infer the peak position
        and height.

        Parameters
        ----------
        min_ridge_len : int, optional
            Minimum length of ridge line to consider a peak,
            by default None. If None, the object attribute 'min_len'
            will be used.

        Returns
        -------
        list
            List of 2-tuples with peak position (sample number) and height.
        """

        # Collect ridges of minimum length 'min_ridge_len'
        peaks = [ (mode(rdg[1])[0][0], np.asscalar(sum(rdg[2]))) 
                    for rdg in self.filter_ridges(min_ridge_len) ]
        return peaks