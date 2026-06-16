# Isotope Matching

The isotope matching workflow establishes links between expected theoretical targets and detected peaks in experimental spectra.

## Data Pre-Filtering and Peak Extraction

Before the matching algorithm maps targets to experimental peaks, the input datasets undergo instrument-specific isolation and parsing steps.
Precomputed target isotopes are filtered dynamically based on the system configuration.
High resolution isotopes are selected for Orbitrap instruments, while low resolution isotopes are chosen for Time-of-Flight instruments.
Experimental peak timeseries data are loaded exclusively within a localized mass tolerance window of 0.5 Da around the target theoretical mass-to-charge values.
The peaks are filtered by polarity if it is specified.
The retrieved timeseries are then collapsed along the temporal dimension to calculate a mean intensity profile, retaining only peaks with positive intensity values.

## Isotope-Peak Assignment and Selection Constraints

The core alignment mechanism operates at the individual isotope level and employs a competitive prioritization strategy governed by a strict hierarchy of structural rules.

### Candidate Sorting and Prioritization

For each target isotope, a list of candidate experimental peaks within the 0.5 Da window is assembled and sorted primarily by absolute mass difference, and secondarily by ascending mass-to-charge value.
The matching engine iterates through the target isotopes in a sequence, prioritizing those with higher theoretical relative abundances and smaller theoretical mass-to-charge ratios.

### Ion-Level Structural Rules
During assignment, several constraints prevent unphysical peak pairings.
Experimental peaks must be entirely unique within a single target ion - multiple isotopes belonging to the same ion are prohibited from sharing the same sample peak.
Different distinct target ions are permitted to independently match against and share the same experimental sample peaks.
When multiple isotopes within the same ion compete for an identical peak, the isotope with the higher theoretical relative abundance takes precedence.
The sequence of assigned experimental peak mass-to-charge coordinates must strictly mirror the sequential order of the theoretical target isotope masses.
An experimental peak will be skipped if its assignment would cause an inversion of the mass order within that specific ion.

## Post-Match Evaluation and Edge Cases

Following the assignment phase, the dataset is split into successfully paired and unmatched groups to finalize the statistical profile.

For all successfully paired isotopes, statistical properties—including abundance errors, mass errors in parts-per-million, and aggregate confidence metrics—are computed according to the standard workflow detailed in [calibration description](calibration.md#quality-assessment-and-scoring).

If an isotope fails to find an experimental peak that satisfies all spatial and structural constraints, it is flagged as unmatched.
The sample mass coordinate for these entries is filled using the original theoretical target mass value, while its final match score is forced to a default value of 0.