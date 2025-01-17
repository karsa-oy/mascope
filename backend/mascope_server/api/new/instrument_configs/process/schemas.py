from pydantic import BaseModel, Field

from mascope_server.api.new.instrument_configs.params import InstrumentConfigParams
from mascope_server.api.new.instrument_configs.schemas import SetInstrumentConfigBody

instrument_config_params = InstrumentConfigParams()


class ProcessInstrumentConfigBody(BaseModel):
    filename: str = Field(
        ..., description="Filename to process instrument functions for"
    )
    instrument_config: SetInstrumentConfigBody = Field(
        ..., description="Instrument configuration to process for the file"
    )
