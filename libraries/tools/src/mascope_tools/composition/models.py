from dataclasses import dataclass, asdict
from mascope_tools.composition.constants import (
    DEFAULT_MAXIMUM_UNSATURATION,
    DEFAULT_MAXIMUM_ROWS,
)


class CompositionFinderException(Exception):
    pass


class CompositionFinderWarning(UserWarning):
    pass


class HeuristicRuleWarning(UserWarning):
    pass


@dataclass
class Atom:
    symbol: str
    min_count: int
    max_count: int
    mass: float


@dataclass
class IonizationMechanism:
    mascope_notation: str
    addition: bool
    formula: str
    charge: int
    mass: float


@dataclass
class SearchContext:
    atoms: list[Atom] = None
    min_inner_mass: float = None
    max_inner_mass: float = None
    neutral_mass: float = None
    mass_range: float = None
    use_unsaturation: bool = False
    min_unsaturation: float = 0.0
    max_unsaturation: float = DEFAULT_MAXIMUM_UNSATURATION
    only_integer_unsaturation: bool = False
    max_result_rows: int = DEFAULT_MAXIMUM_ROWS
    ionization_mechanism: IonizationMechanism | None = None
    target_monoisotopic_mass: float = None
    results_found: int = 0


@dataclass
class Result:
    formula: str
    neutral_mass: float
    error_ppm: float
    ion: str | None
    ionization_mechanism: str | None
    observed_mass: float
    unsaturation: float | None = None
    other_candidates: list[str] | None = None

    def to_dict(self):
        d = asdict(self)
        # Remove None values for optional fields
        return {k: v for k, v in d.items() if v is not None}
