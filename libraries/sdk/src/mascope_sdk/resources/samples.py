"""Samples resource for the Mascope SDK."""

from __future__ import annotations

from typing import Any

from ._base import BaseResource


class SamplesResource(BaseResource):
    """Resource for sample operations.

    Provides methods to retrieve sample data, spectra, peaks, and timeseries.
    Samples represent individual measurement files within a sample batch.

    Example::

        from mascope_sdk import MascopeClient

        mascope = MascopeClient()

        # List samples in a batch
        samples = mascope.samples.list(batch_id="batch-123")

        # Get spectrum data
        spectrum = mascope.samples.get_spectrum(sample_id="sample-456")

        # Get peak data
        peaks = mascope.samples.get_peaks(sample_id="sample-456")
    """

    def list(self, batch_id: str) -> list[dict]:
        """List all samples in a sample batch.

        :param batch_id: The ID of the sample batch to list samples from.
        :type batch_id: str
        :return: A list of sample dictionaries, each containing at least:

                 - ``id``: Unique sample identifier
                 - ``name``: Sample name
                 - Additional sample metadata
        :rtype: list[dict]
        :raises AuthenticationError: If authentication fails.
        :raises NotFoundError: If the batch is not found.
        :raises MascopeAPIError: If the API request fails.

        Example::

            samples = mascope.samples.list(batch_id="batch-123")
            for sample in samples:
                print(f"Sample: {sample['name']} (ID: {sample['id']})")
        """
        return self._get("samples", params={"sample_batch_id": batch_id}) or []

    def get(self, sample_id: str) -> dict | None:
        """Get details of a specific sample.

        :param sample_id: The ID of the sample to retrieve.
        :type sample_id: str
        :return: A dictionary containing the sample details, or None if not found.
        :rtype: dict | None
        :raises AuthenticationError: If authentication fails.
        :raises NotFoundError: If the sample is not found.
        :raises MascopeAPIError: If the API request fails.

        Example::

            sample = mascope.samples.get(sample_id="sample-456")
            print(f"Sample: {sample['name']}")
            print(f"Polarity: {sample.get('polarity')}")
        """
        return self._get(f"samples/{sample_id}")

    def get_peaks(
        self,
        sample_id: str,
        *,
        areas: bool = True,
        heights: bool = True,
        average: bool = True,
        matches: bool = False,
        t_min: float | None = None,
        t_max: float | None = None,
        mz_min: float | None = None,
        mz_max: float | None = None,
    ) -> dict | None:
        """Get peak data from a sample.

        Retrieves detected peaks with automatic polarity filtering based on
        sample metadata. Supports optional time and m/z range filtering.

        :param sample_id: The ID of the sample to retrieve peaks from.
        :type sample_id: str
        :param areas: Include peak areas (integrated intensity). Defaults to True.
        :type areas: bool
        :param heights: Include peak heights (max intensity). Defaults to True.
        :type heights: bool
        :param average: Return averaged data across time. Defaults to True.
        :type average: bool
        :param matches: Include matched compounds/ions/isotopes. Defaults to False.
        :type matches: bool
        :param t_min: Minimum time in seconds. Uses sample start if not provided.
        :type t_min: float, optional
        :param t_max: Maximum time in seconds. Uses sample end if not provided.
        :type t_max: float, optional
        :param mz_min: Minimum m/z value for filtering.
        :type mz_min: float, optional
        :param mz_max: Maximum m/z value for filtering.
        :type mz_max: float, optional
        :return: A dictionary containing:

                 - ``mz``: List of m/z values
                 - ``area``: List of peak areas (if requested)
                 - ``height``: List of peak heights (if requested)
                 - ``match``: List of matched compounds (if requested)

                 Returns None if no peaks are found.
        :rtype: dict | None
        :raises AuthenticationError: If authentication fails.
        :raises NotFoundError: If the sample is not found.
        :raises MascopeAPIError: If the API request fails.

        Example::

            # Get all peaks
            peaks = mascope.samples.get_peaks(sample_id="sample-456")

            # Get peaks in a specific m/z range
            peaks = mascope.samples.get_peaks(
                sample_id="sample-456",
                mz_min=100,
                mz_max=200,
            )

            # Get peaks with match information
            peaks = mascope.samples.get_peaks(
                sample_id="sample-456",
                matches=True,
            )
        """
        params: dict[str, Any] = {
            "areas": str(areas).lower(),
            "heights": str(heights).lower(),
            "average": str(average).lower(),
            "matches": str(matches).lower(),
        }
        # Add optional range parameters
        if t_min is not None:
            params["t_min"] = t_min
        if t_max is not None:
            params["t_max"] = t_max
        if mz_min is not None:
            params["mz_min"] = mz_min
        if mz_max is not None:
            params["mz_max"] = mz_max

        return self._get(f"samples/{sample_id}/peaks", params=params)

    def get_peak_timeseries(
        self,
        sample_id: str,
        mz: float,
        *,
        mz_tolerance_ppm: float = 1.0,
        t_min: float | None = None,
        t_max: float | None = None,
    ) -> dict | None:
        """Get timeseries data for a specific peak.

        Retrieves intensity values over time for a peak at the specified m/z value.
        Uses automatic polarity filtering based on sample metadata.

        :param sample_id: The ID of the sample.
        :type sample_id: str
        :param mz: The m/z value of the peak.
        :type mz: float
        :param mz_tolerance_ppm: m/z tolerance in ppm for peak matching. Defaults to 1.0.
        :type mz_tolerance_ppm: float
        :param t_min: Minimum time in seconds. Uses sample start if not provided.
        :type t_min: float, optional
        :param t_max: Maximum time in seconds. Uses sample end if not provided.
        :type t_max: float, optional
        :return: A dictionary containing:

                 - ``mz``: Actual m/z of the matched peak (None if no match)
                 - ``height``: List of intensity values over time
                 - ``time``: List of time points in seconds

                 Returns None if no matching peak is found.
        :rtype: dict | None
        :raises AuthenticationError: If authentication fails.
        :raises NotFoundError: If the sample is not found.
        :raises MascopeAPIError: If the API request fails.

        Example::

            # Get timeseries for a peak at m/z 180.063
            timeseries = mascope.samples.get_peak_timeseries(
                sample_id="sample-456",
                mz=180.063,
                mz_tolerance_ppm=5.0,
            )

            if timeseries:
                import matplotlib.pyplot as plt
                plt.plot(timeseries['time'], timeseries['height'])
                plt.xlabel('Time (s)')
                plt.ylabel('Intensity')
                plt.show()
        """
        body: dict[str, Any] = {
            "peak_mz": mz,
            "peak_mz_tolerance_ppm": mz_tolerance_ppm,
        }
        if t_min is not None:
            body["t_min"] = t_min
        if t_max is not None:
            body["t_max"] = t_max

        return self._post(f"samples/{sample_id}/peaks/timeseries", data=body)

    def get_spectrum(
        self,
        sample_id: str,
        *,
        t_min: float | None = None,
        t_max: float | None = None,
        mz_min: float | None = None,
        mz_max: float | None = None,
    ) -> dict | None:
        """Get spectrum data from a sample.

        Retrieves the averaged mass spectrum with automatic polarity filtering.
        The spectrum represents intensities averaged across all matching scans
        in the specified time window.

        :param sample_id: The ID of the sample.
        :type sample_id: str
        :param t_min: Minimum time in seconds. Uses sample start if not provided.
        :type t_min: float, optional
        :param t_max: Maximum time in seconds. Uses sample end if not provided.
        :type t_max: float, optional
        :param mz_min: Minimum m/z value for filtering.
        :type mz_min: float, optional
        :param mz_max: Maximum m/z value for filtering.
        :type mz_max: float, optional
        :return: A dictionary containing:

                 - ``mz``: List of m/z values
                 - ``intensity``: List of intensity values
                 - ``intensity_unit``: Unit of intensity measurements

                 Returns None if no spectrum data is found.
        :rtype: dict | None
        :raises AuthenticationError: If authentication fails.
        :raises NotFoundError: If the sample is not found.
        :raises MascopeAPIError: If the API request fails.

        Example::

            # Get full spectrum
            spectrum = mascope.samples.get_spectrum(sample_id="sample-456")

            # Get spectrum in a specific m/z range
            spectrum = mascope.samples.get_spectrum(
                sample_id="sample-456",
                mz_min=100,
                mz_max=500,
            )

            # Plot the spectrum
            import matplotlib.pyplot as plt
            plt.stem(spectrum['mz'], spectrum['intensity'])
            plt.xlabel('m/z')
            plt.ylabel(f"Intensity ({spectrum['intensity_unit']})")
            plt.show()
        """
        params: dict[str, Any] = {}
        if t_min is not None:
            params["t_min"] = t_min
        if t_max is not None:
            params["t_max"] = t_max
        if mz_min is not None:
            params["mz_min"] = mz_min
        if mz_max is not None:
            params["mz_max"] = mz_max

        return self._get(f"samples/{sample_id}/spectrum", params=params or None)

    def get_spectra(
        self,
        sample_ids: list[str],
        *,
        t_min: float | None = None,
        t_max: float | None = None,
        mz_min: float | None = None,
        mz_max: float | None = None,
    ) -> list[dict] | None:
        """Get spectra for multiple samples.

        Retrieves averaged spectra for a list of samples with optional filtering.
        Useful for comparing spectra across multiple samples.

        :param sample_ids: List of sample IDs to retrieve spectra for.
        :type sample_ids: list[str]
        :param t_min: Minimum time in seconds.
        :type t_min: float, optional
        :param t_max: Maximum time in seconds.
        :type t_max: float, optional
        :param mz_min: Minimum m/z value for filtering.
        :type mz_min: float, optional
        :param mz_max: Maximum m/z value for filtering.
        :type mz_max: float, optional
        :return: A list of spectrum dictionaries, one per sample.
                 Returns None if no data is found.
        :rtype: list[dict] | None
        :raises AuthenticationError: If authentication fails.
        :raises MascopeAPIError: If the API request fails.

        Example::

            spectra = mascope.samples.get_spectra(
                sample_ids=["sample-1", "sample-2", "sample-3"]
            )
        """
        params: dict[str, Any] = {"sample_item_ids": sample_ids}
        if t_min is not None:
            params["t_min"] = t_min
        if t_max is not None:
            params["t_max"] = t_max
        if mz_min is not None:
            params["mz_min"] = mz_min
        if mz_max is not None:
            params["mz_max"] = mz_max

        return self._get("samples/spectra", params=params)

    def get_centroids(self, sample_ids: list[str]) -> dict | None:
        """Get centroid data for multiple samples.

        Retrieves per-scan centroid data for the specified samples.

        :param sample_ids: List of sample IDs to retrieve centroids for.
        :type sample_ids: list[str]
        :return: A dictionary containing centroid data keyed by sample ID.
                 Returns None if no data is found.
        :rtype: dict | None
        :raises AuthenticationError: If authentication fails.
        :raises MascopeAPIError: If the API request fails.
        """
        return self._get("samples/centroids", params={"sample_item_ids": sample_ids})
