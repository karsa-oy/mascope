import pandas as pd
from mascope_tools.composition.finder import assign_compositions
from .data_extractor import DataExtractor


class CompositionMap:
    def __init__(
        self, data: DataExtractor, composition_params: dict, heuristic_params: dict
    ):
        """Computes compositions for ms2 averaged peaks/centroids

        :param data: DataExtractor object containing the MS2 spectra and parent peaks
        :type data: DataExtractor
        :param composition_params: Parameters for composition assignment
        :type composition_params: dict
        :param heuristic_params: Additional heuristic parameters for composition assignment
        :type heuristic_params: dict
        """
        self._data = data
        self._composition_params = composition_params
        self._heuristic_params = heuristic_params

        self.matches = {}
        for pp in data.parent_peaks:
            mz = data.ms2_spectra[pp].mz
            intensity = data.ms2_spectra[pp].intensity
            ms2_peak_df = pd.DataFrame({"mz": mz, "intensity": intensity})

            assigned_peaks, _ = assign_compositions(
                ms2_peak_df,
                self._composition_params.copy(),
                self._heuristic_params.copy(),
            )

            self.matches[pp] = assigned_peaks.sort_values("mz").reset_index(drop=True)
