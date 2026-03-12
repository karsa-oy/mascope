import pytest
from mascope_backend.api.controllers.calibration.lib.calibration_mz_fit import (
    TofCalibrationHandler,
    OrbiCalibrationHandler,
    get_calibration_handler,
    calibration_params_factory,
)
from mascope_backend.api.models.calibration.calibration_pydantic_model import (
    CalibrationFitParams,
    TofCalibrationParams,
    OrbiCalibrationParams,
)


def _make_params(polarity="+"):
    return CalibrationFitParams(
        refine_window=10,
        calibration_collection_id="cc_1",
        ionization_mechanism_ids=["im_1"],
        polarity=polarity,
    )


class TestGetCalibrationHandler:

    def test_tof_returns_tof_handler(self):
        handler = get_calibration_handler("tofwerk", _make_params(), None)
        assert isinstance(handler, TofCalibrationHandler)

    def test_orbi_returns_orbi_handler(self):
        handler = get_calibration_handler("orbitrap", _make_params(), None)
        assert isinstance(handler, OrbiCalibrationHandler)

    def test_unknown_instrument_raises(self):
        with pytest.raises(
            ValueError, match="Failed to get instrument type for instrument fake"
        ):
            get_calibration_handler("fake", _make_params(), None)


class TestCalibrationParamsFactory:

    def test_tof_returns_tof_params_with_defaults(self):
        params = calibration_params_factory("tofwerk")
        assert isinstance(params, TofCalibrationParams)

    def test_orbi_returns_orbi_params_with_defaults(self):
        params = calibration_params_factory("orbitrap")
        assert isinstance(params, OrbiCalibrationParams)

    def test_unknown_instrument_raises(self):
        with pytest.raises(
            ValueError, match="Failed to get instrument type for instrument fake"
        ):
            calibration_params_factory("fake")
