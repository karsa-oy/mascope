from pydantic import BaseModel

from ..match.params import MatchParams


class Params(BaseModel):
    match: MatchParams = MatchParams()
