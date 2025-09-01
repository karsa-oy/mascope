from dataclasses import dataclass, asdict
from mascope_tools.composition.constants import (
    DEFAULT_MAXIMUM_UNSATURATION,
    DEFAULT_MAXIMUM_ROWS,
    DEFAULT_SEARCH_ELEMENT_COUNT_RANGES,
    DEFAULT_MASS_RANGE_THRESHOLD_PPM,
)
from mascope_tools.composition import utils


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
    ion_shift: float = 0.0
    target_monoisotopic_mass: float = None
    results_found: int = 0

    def build(self, params: dict):
        self.mass_range = float(
            params.get("mass_range_ppm", DEFAULT_MASS_RANGE_THRESHOLD_PPM)
        )
        self.max_result_rows = int(params.get("max_result_rows", DEFAULT_MAXIMUM_ROWS))
        self.element_count_ranges = params.get(
            "element_count_ranges", DEFAULT_SEARCH_ELEMENT_COUNT_RANGES
        )
        self.min_unsaturation = float(params.get("min_unsaturation", 0))
        self.max_unsaturation = float(params.get("max_unsaturation", 50))
        self.only_integer_unsaturation = utils.parse_bool(
            params.get("only_integer_unsaturation", False)
        )
        self.use_unsaturation = utils.parse_bool(params.get("use_unsaturation", False))
        self.target_monoisotopic_mass = float(
            params.get(
                "monoisotopic_mass", params.get("target_monoisotopic_mass", "-1")
            )
        )


@dataclass
class Result:
    formula: str
    neutral_mass: float
    composition_error_ppm: float
    ion: str | None
    ionization_mechanism: str | None
    observed_mass: float
    unsaturation: float | None = None
    other_candidates: list[str] | None = None

    def to_dict(self):
        d = asdict(self)
        # Remove None values for optional fields
        return {k: v for k, v in d.items() if v is not None}
