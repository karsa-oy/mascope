from pydantic import BaseModel

from mascope_match.params import MatchParams
from mascope_backend.api.new.instrument_configs.params import InstrumentConfigParams
from mascope_backend.api.new.cheminfo.config import ChemInfoConfig


class Params(BaseModel):
    match: MatchParams = MatchParams()
    instrument_config: InstrumentConfigParams = InstrumentConfigParams()
    cheminfo_config: ChemInfoConfig = ChemInfoConfig()
