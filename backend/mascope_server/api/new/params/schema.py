from pydantic import BaseModel

from ..match.params import MatchParams
from ..instrument_functions.params import InstrumentFunctionParams


class Params(BaseModel):
    match: MatchParams = MatchParams()
    instrument_functions: InstrumentFunctionParams = InstrumentFunctionParams()
