from datetime import datetime, timezone

from mascope_backend.api.new.instrument_configs.schemas import (
    InstrumentConfigFitParams,
    PeakShape,
)
from mascope_backend.api.new.instrument_configs.service import fit_instrument_functions
from mascope_backend.file_converter.base_processor import (
    BaseFileProcessor,
    SampleFileProps,
    with_file_context,
)
from mascope_thermo.thermo import RawFileManager, get_polarity_options


class RawProcessor(BaseFileProcessor):
    """Reads and processes Orbi raw files"""

    def __init__(
        self,
        socket_client,
        file_queue,
        shutdown_event,
        peak_guard=None,
    ):
        super().__init__(
            socket_client=socket_client,
            file_queue=file_queue,
            shutdown_event=shutdown_event,
            peak_guard=peak_guard,
        )

    @property
    def file_extension(self) -> str:
        """Get the file extension for raw files

        :return: File extension
        :rtype: str
        """
        return ".raw"

    @property
    @with_file_context
    def filename(self) -> str:
        """Base filename of the raw file currently being processed

        :return: Base filename
        :rtype: str
        """
        filename = self._strip_filepath(self.file_handle.FileName).replace(" ", "_")
        timestamp = datetime.fromisoformat(self.timestamp).strftime(
            "%Y.%m.%d-%Hh%Mm%Ss"
        )
        # Add timestamp to the filename
        return filename.replace("_", f"_{timestamp}_", 1)

    @property
    @with_file_context
    def interval(self) -> float:
        """Mean measurement interval in seconds, i.e. length of one spectrum in the sample

        :return: Measurement interval [s]
        :rtype: float
        """
        scans = self.file_handle.RunHeaderEx.LastSpectrum
        return self.length / scans  # [s]

    @property
    @with_file_context
    def length(self) -> float:
        """Length of the sample file in seconds

        :return: Sample length [s]
        :rtype: float
        """
        return self.file_handle.RunHeaderEx.EndTime * 60.0  # [s]

    @property
    @with_file_context
    def method_file(self) -> str:
        """Instrument method file name from the raw file

        :return: Instrument method file name
        :rtype: str
        """
        method_file = self.file_handle.SampleInformation.InstrumentMethodFile
        return method_file if method_file else ""

    @property
    @with_file_context
    def mz_calibration(self) -> None:
        """M/z calibration coefficient is not applicable for Orbi files

        :return: None
        :rtype: None
        """
        return None

    @property
    @with_file_context
    def range(self) -> list:
        """M/z range of the sample file

        :return: M/z range
        :rtype: list
        """
        return [
            self.file_handle.RunHeaderEx.LowMass,
            self.file_handle.RunHeaderEx.HighMass,
        ]

    @property
    @with_file_context
    def polarity(self) -> str:
        """Polarity options in the sample file

        :return: Polarity options
        :rtype: str
        """
        return get_polarity_options(self.file_handle.FileName)

    @property
    def sample_interval(self) -> None:
        """Sample interval is not applicable for Orbi files

        :return: None
        :rtype: None
        """
        return None

    @property
    def single_ion_signal(self) -> None:
        """Single ion signal is not applicable for Orbi files

        :return: None
        :rtype: None
        """
        return None

    @property
    @with_file_context
    def timestamp(self) -> str:
        """Timestamp in isoformat, local timezone

        :return: Timestamp
        :rtype: str
        """
        dotnet_datetime = self.file_handle.CreationDate

        python_datetime = datetime(
            year=dotnet_datetime.Year,
            month=dotnet_datetime.Month,
            day=dotnet_datetime.Day,
            hour=dotnet_datetime.Hour,
            minute=dotnet_datetime.Minute,
            second=dotnet_datetime.Second,
        )
        return python_datetime.isoformat()

    @property
    def utc_offset(self) -> int:
        """UTC offset in seconds

        # TODO: Currently there is no way to get the UTC offset from the raw file.
        # This implementation assumes local timezone.

        :return: UTC offset [s]
        :rtype: int
        """
        now = datetime.now()
        utc_offset = (now - now.astimezone(timezone.utc).replace(tzinfo=None)).seconds
        return utc_offset

    @staticmethod
    def _file_context_manager(file_path: str):
        """Context manager for raw files

        :param file_path: Path to the raw file
        :return: Raw file handle
        :rtype: RawFileManager
        """
        return RawFileManager(file_path)

    def _process_instrument_config(
        self, sample_file_props: SampleFileProps
    ) -> tuple[any, any, any, any]:
        """Fit instrument functions"""
        dmz = 0.01
        fit_params = InstrumentConfigFitParams()
        (
            peakshape_numpy,
            resolution_function_partial,
            _,
        ) = fit_instrument_functions(
            sample_file_props.filename, r_sq_thres=fit_params.threshold, dmz=dmz
        )

        # Convert peakshape to lists to be serialized
        peakshape = PeakShape(
            x=peakshape_numpy["x"].tolist(), y=peakshape_numpy["y"].tolist()
        )

        # Get resolution function coefficients
        partial_coefficients = (
            resolution_function_partial.keywords  # pylint: disable=no-member
        )
        resolution_function = [partial_coefficients["a"]]

        return (
            peakshape,
            resolution_function,
            peakshape_numpy,
            resolution_function_partial,
        )
