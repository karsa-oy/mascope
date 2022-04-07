import numpy as np
import pandas as pd

from karsalib.chemistry import match_mz

def identify_matches(peak_mzs, peak_heights, target_isotope_df, mz_tolerance):
    """Find matching targets for found peaks

    Parameters
    ----------
    peak_mzs : list
        List of found peak m/z values
    peak_heights : list
        List of found peak intensities
    target_isotope_df : pandas.DataFrame
        Target isotope data
    mz_tolerance : float
        m/z error tolerance when finding matches, in ppm

    Returns
    -------
    pandas.DataFrame
        Input dataframe with added columns for 'peak id', 'peak mz' and 'peak height',
        containing measured values for matched targets, nan where no matching peak was found.

    Raises
    ------
    NotImplementedError
        Case where more than one peak matches the same target not implemented yet.
    """
    # Initialize match dataframe from target isotope dataframe
    isotope_match_df = target_isotope_df
    isotope_match_df.loc[:, 'samplePeakId'] = np.nan
    isotope_match_df.loc[:, 'samplePeakMz'] = np.nan
    isotope_match_df.loc[:, 'samplePeakHeight'] = np.nan
    peak_sorting = np.argsort(peak_mzs)

    for target_isotope_index, target_isotope_row in isotope_match_df.iterrows():
        target_mz = target_isotope_row.mz
        match_indeces, match_mzs = match_mz(target_mz,
                                       peak_mzs[peak_sorting],
                                       tolerance=mz_tolerance
                                       )
        for match_index in match_indeces:
            peak_index = peak_sorting[match_index]
            peak_mz = peak_mzs[peak_index]
            peak_height = peak_heights[peak_index]
            if not np.isnan(isotope_match_df.loc[target_isotope_index, 'samplePeakId']):
                prev_mz_err = np.abs(isotope_match_df.loc[target_isotope_index, 'samplePeakMz'] - target_mz)
                new_mz_err = np.abs(peak_mz - target_mz)
                if new_mz_err > prev_mz_err:
                    continue
            isotope_match_df.loc[target_isotope_index, 'samplePeakId'] = peak_index
            isotope_match_df.loc[target_isotope_index, 'samplePeakMz'] = peak_mz
            isotope_match_df.loc[target_isotope_index, 'samplePeakHeight'] = peak_height

    isotope_match_df = isotope_match_df.dropna(subset=['samplePeakMz'])

    return isotope_match_df

def calculate_match_stats(isotope_match_df, sample_item, iso_abu_tolerance, mz_tolerance):
    """Calculate measured isotope ratios and mz errors

    Parameters
    ----------
    match_df : pandas.DataFrame
        Target ion dataframe with columns for measured 'peak mz' and 'peak height'

    Returns
    -------
    pandas.DataFrame
        Input dataframe with added columns 'rel peak height', 'iso abu error', 'mz error'
    """
    isotope_match_df.loc[:, 'relPeakHeight'] = np.nan 
    isotope_match_df.loc[:, 'isoAbuError'] = np.nan
    isotope_match_df.loc[:, 'mzError'] = np.nan
    isotope_match_df.loc[:, 'matchScore'] = np.nan

    # STEP 1 - Select good isotope level matches
        
    # calculate isotope ratios

    # sum matched sample peak heights for each ion
    ion_level_peak_sums = isotope_match_df \
        .groupby(['targetIonId'], as_index=False)['samplePeakHeight'] \
        .sum()

    # join sums back to the isotope level
    isotope_level_peak_sums = pd.merge(
        isotope_match_df, 
        ion_level_peak_sums\
            .rename(columns={'samplePeakHeight': 'samplePeakHeightSum'}),
        on=['targetIonId'], how='outer'
    )

    # compute relative peak heights
    isotope_match_df.loc[:, 'relPeakHeight'] = \
        isotope_match_df['samplePeakHeight'] / isotope_level_peak_sums['samplePeakHeightSum']

    # calculate isotope ratio errors
    isotope_match_df.loc[:, 'isoAbuError'] =  \
        isotope_match_df['relAbu'] * ( isotope_match_df['relPeakHeight'] - isotope_match_df['relAbu'] )

    # select matches based on threshold
    isotope_match_df = isotope_match_df[np.abs(isotope_match_df['isoAbuError']) <= iso_abu_tolerance]

    # STEP 2 - Calculate isotope level stats

    # calculate mz errors
    isotope_match_df.loc[:, 'mzError'] = \
        1e6 * ( isotope_match_df['samplePeakMz'] - isotope_match_df['mz'] ) / isotope_match_df['samplePeakMz']

    # isotope level match score
    isotope_match_df.loc[:, 'matchScore'] = \
        ( 1 - isotope_match_df['isoAbuError'] ) * ( 1 - abs(isotope_match_df['mzError']) / mz_tolerance )
    # append sample id
    isotope_match_df.loc[:, 'sampleItemId'] = sample_item['id']

    # STEP 3 - Calculate ion level stats

    # ion level score is the sum of isotope relative abundances
    ion_match_df = isotope_match_df \
        .groupby(['targetIonId', 'targetCompoundId']) \
        .agg( \
            matchScore = ('relAbu', 'sum'), \
            samplePeakHeight = ('samplePeakHeight', 'sum') \
            ) \
        .reset_index()
    # append sample id
    ion_match_df.loc[:, 'sampleItemId'] = sample_item['id']

    # save ion level peak sums 
    ion_match_df.loc[:, 'samplePeakHeight'] = ion_level_peak_sums

    # STEP 4 - Calculate compound level stats

    # compound level aggregation
    compound_match_df = ion_match_df \
        .groupby(['targetCompoundId']) \
        .agg( \
            matchScore = ('matchScore', 'max'), \
            samplePeakHeight = ('samplePeakHeight', 'sum') \
            ) \
        .reset_index()
    # append sample id
    compound_match_df.loc[:, 'sampleItemId'] = sample_item['id']

    # STEP 5 - Format output

    output = lambda df: list(df.to_dict(orient='index').values())
    match_stats = {
        'isotope': output(isotope_match_df),
        'ion': output(ion_match_df),
        'compound': output(compound_match_df)
    }

    return match_stats