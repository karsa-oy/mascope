from pydantic import BaseModel

from ..match.params import MatchParams
from ..instrument_configs.params import InstrumentConfigParams


class Params(BaseModel):
    match: MatchParams = MatchParams()
    instrument_config: InstrumentConfigParams = InstrumentConfigParams()
