from pydantic import BaseModel

from mascope_backend.api.new.cheminfo.config import ChemInfoConfig
from mascope_match.params import MatchParams


class Params(BaseModel):
    match: MatchParams = MatchParams()
    cheminfo_config: ChemInfoConfig = ChemInfoConfig()
