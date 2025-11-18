from pydantic import BaseModel, Field


class SampleFileProps(BaseModel):
    """Sample file properties extracted from processed files."""

    filename: str = Field(description="Name of the file being processed")

    interval: float = Field(
        description="Mean measurement interval in seconds, i.e. length of a spectrum in the sample."
    )

    length: float = Field(description="Length of the sample file in seconds.")

    method_file: str = Field(description="Method file name from the file.")

    mz_calibration: dict | None = Field(description="Mass calibration properties.")

    range: list = Field(description="m/z range of the sample file.")

    polarity: str = Field(description="Polarity from the file.")

    sample_interval: float | None = Field(
        description=(
            "Sample interval in nanoseconds. The interval between two consecutive samples"
            "in the time-of-flight dimension. Not to be confused with measurement interval"
            "(interval property) which is the time between two consecutive spectra in the sample (i.e."
            "chromatographic dimension). Not known for the Orbitrap files."
        )
    )

    single_ion_signal: float | None = Field(
        description=(
            "Single ion signal [mV*ns/ion]. The signal produced by a single ion in the detector."
            "Not known for the Orbitrap files."
        )
    )

    timestamp: str = Field(description="Timestamp from the file in ISO format.")

    utc_offset: float = Field(description="Timestamp UTC offset in seconds.")
