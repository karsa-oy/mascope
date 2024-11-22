def resolve_instrument_type(instrument_name: str) -> str:
    """Get instrument type (one of {"orbi", "tof"}) from an instrument name

    :param instrument_name: instrument name
    :type instrument: str
    :raises ValueError: Failed to detect instrument type
    :return: Instrument type, one of {"orbi", "tof"}
    :rtype: str
    """
    name = instrument_name.lower()
    if "orbi" in name:
        instrument_type = "orbi"
    elif "tof" in name or "api" in name:
        instrument_type = "tof"
    else:
        raise ValueError(
            f"Failed to get instrument type for instrument {instrument_name}"
        )
    return instrument_type
