from datetime import datetime
import os
import numpy as np
from scipy.stats import skewnorm, poisson
import xarray as xr
import mascope_runtime as runtime

logger = runtime.logger.service("backend")


# Precompute sigma multiplier for peak generation
SIGMA_MULTIPLIER = 2 * np.sqrt(2 * np.log(2))


class GenerationParams:
    """Parameters used for spectra generation"""

    def __init__(
        self,
        ms: str,
        seed=None,
        n_peaks=100,
        mz_range=(100, 1000),
        hei_range=(1e1, 1e6),
    ):
        """Set parameters for spectra generation
        At least 1000 peaks are required for TOF to get overlapings

        :param ms: spectrometer type, tof or orbi
        :type ms: str
        :param seed: random seed value, defaults to None
        :type seed: int, optional
        :param n_peaks: number of peaks per spectrum, defaults to 100
        :type n_peaks: int, optional
        :param mz_range: m/z range (min, max), defaults to (100, 1000)
        :type mz_range: tuple, optional
        :param hei_range: height range (min, max), defaults to (1e1, 1e6)
        :type hei_range: tuple, optional
        :raises NameError: if the type of spectrometer is unknown
        """
        self.ms = ms
        self.seed = seed
        self.n_peaks = n_peaks
        self.mz_range = mz_range
        self.hei_range = hei_range

        if self.ms == "tof":
            self.a = 1e-4
            self.b = 1e-3
            self.alpha = 2  # peak skeweness
            self.points_per_fwhm = 10
        elif self.ms == "orbi":
            self.a = 1.715e6
            self.b = None
            self.alpha = None
            self.points_per_fwhm = 4
        else:
            raise NameError(f"Unknown mass spectrometer {ms}. Choose tof or orbi")

    def vary_params(self, val=5.0):
        """Vary resolution function coefficient and number of peaks
        in range var+-val using randomiser rng. val in %

        :param val: defines the range to vary a variable in, defaults to 5%
        :type val: float, optional
        """
        #
        # Init randomizer
        rng = np.random.default_rng()
        # Update resolution coefficients
        self.a *= 1 + rng.uniform(-val / 100, val / 100)
        self.b *= 1 + rng.uniform(-val / 100, val / 100)
        # Update number of peaks
        self.n_peaks *= 1 + rng.uniform(-val / 100, val / 100)

    def show_params(self):
        """Print current parameters"""
        print(
            f"""
            Mass spectrometer type is {self.ms}
            Random seed is {self.seed}
            Number of peaks is set to {self.n_peaks}
            m/z range {self.mz_range}
            Peak height range {self.hei_range}
            Points per FWHM (orbi only) {self.points_per_fwhm}
            Resolution funtion coefficients:
                a = {self.a}
                b = {self.b} (tof only)
            Skeweness of peaks {self.alpha} (tof only)
            """
        )

    def to_dict(self):
        """Get attributes as a dict"""
        return {
            "ms_type": self.ms,
            "random_seed": self.seed,
            "n_peaks": self.n_peaks,
            "mz_range": self.mz_range,
            "hei_range": self.hei_range,
            "points_per_fwhm": self.points_per_fwhm,
            "res_fun_coef_a": self.a,
            "res_fun_coef_b": self.b,
            "skeweness": self.alpha,
        }


class SpectraGenerator:
    """Class for generation of artificial spectra"""

    def __init__(self, params, seed=None):
        """Init spectra generator

        :param params: parameters for spectra generation
        :type params: GenerationParams
        :param seed: random seed value, defaults to None
        :type seed: int, optional
        """
        # Save initial parameters
        self.params = params
        # Init randomizer
        self.rng = np.random.default_rng(seed=seed)
        # Init spectrum and peaks
        self.peaks = {}
        self.spec = None
        # Precompute mz grid
        self.mz_grid = self._precompute_grid()
        # Init noize level (used in tof only)
        self.noise = None

    def _precompute_grid(self):
        """Precompute mz grid based on the resolution function"""
        mz_min, mz_max = sorted(self.params.mz_range)
        # Set starting mz value
        mz = mz_min
        # Initialize list with mz grid
        mz_grid = [mz_min]
        while mz < mz_max:
            resolution = self._get_res_fun(mz)
            fwhm = mz / resolution
            # Step to the next point of the grid
            step = fwhm / self.params.points_per_fwhm
            # Add a new point to the mz grid
            mz += step
            mz_grid.append(mz)

        return np.array(mz_grid, dtype=np.float32)

    def _get_res_fun(self, mz: np.ndarray):
        """Calculate resolving power values at a given m/z value or array"""
        if self.params.ms == "orbi":
            return self.params.a / np.sqrt(mz)
        if self.params.ms == "tof":
            return mz / (self.params.a * mz + self.params.b)

    def generate_spec(self):
        """Add Gaussian peaks with specified parameters to spectrum"""
        # Generate peak positions indices based on mz_grid
        mask_positions = self.rng.integers(0, len(self.mz_grid), self.params.n_peaks)
        # Filter out repetetive position indices
        mask_positions = np.unique(mask_positions)
        # Sort peak positions
        positions = np.sort(self.mz_grid[mask_positions])

        # Generate and scale heights
        heights = self.rng.power(0.01, positions.size)
        heights = np.interp(
            heights,
            (heights.min(), heights.max()),
            sorted(self.params.hei_range),
        )

        resolutions = self._get_res_fun(positions)
        sigmas = positions / resolutions / SIGMA_MULTIPLIER

        # Save generated parameters
        self.peaks["poss"] = positions
        self.peaks["heis"] = heights

        # generate pure Gaussian peaks
        if self.params.ms == "orbi":

            peaks = [
                heights[i]
                * np.exp(-0.5 * ((self.mz_grid - positions[i]) / sigmas[i]) ** 2)
                for i in range(self.params.n_peaks)
            ]
            self.spec = np.sum(peaks, axis=0)

        # Generate skewed Gaussian peaks
        if self.params.ms == "tof":
            self.spec = np.zeros_like(self.mz_grid)
            for i in range(self.params.n_peaks):
                # Create normalized peak shape, then scale height
                skewnorm_pdf = skewnorm.pdf(
                    self.mz_grid, a=self.params.alpha, loc=positions[i], scale=sigmas[i]
                )
                self.spec += heights[i] * skewnorm_pdf / skewnorm_pdf.max()

            # Add Poisson noise
            noise = poisson.rvs(mu=np.sqrt(self.spec).mean(), size=self.spec.shape)
            self.spec += noise

        return self.spec

    def to_zarr(self, path: str):
        """Save spectrum to zarr file at path"""
        if self.spec is None:
            logger.warning("Nothing to save. Generate spectrum first!")

        # Create main xarray.Dataset and add metadata
        ds = xr.Dataset(coords={"mz": self.mz_grid}, attrs=self.params.to_dict())

        # Create spectrum variable
        spec_arr = xr.DataArray(
            data=self.spec, coords={"mz": self.mz_grid}, dims=["mz"]
        )

        # Create variable for peak heights
        true_heights = xr.DataArray(
            data=self.peaks["heis"], coords={"mz": self.peaks["poss"]}, dims=["mz"]
        )
        # Reindex true_heights to align with the full x coordinate
        true_heights = true_heights.reindex({"mz": self.mz_grid})

        # Add arrays to dataset
        ds["sum_signal"] = spec_arr
        ds["true_peak_heis"] = true_heights

        # Save to zarr file
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M%S")
        filename = f"{self.params.ms}_test_file_{date_str}_{time_str}.zarr"
        ds.to_zarr(os.path.join(path, filename), mode="w")
