"""Name-to-ID resolution utilities for the Mascope SDK."""

import pandas as pd


def resolve_id(
    value: str,
    items: pd.DataFrame | None,
    id_column: str,
    name_column: str,
    entity_label: str,
) -> str:
    """Resolve a name or substring to a unique ID.

    Checks for an exact ID match first, then falls back to case-insensitive
    matching on the name column. The match uses ``pandas.Series.str.contains``,
    so *value* can be a plain substring **or** a regular expression
    (e.g. ``"2026-01|2026-02"``).

    Raises if zero or multiple matches.

    :param value: The name, substring, or regex pattern to resolve (or an exact ID).
    :type value: str
    :param items: DataFrame of available items to match against.
    :type items: pd.DataFrame | None
    :param id_column: Column name containing the IDs.
    :type id_column: str
    :param name_column: Column name containing the names.
    :type name_column: str
    :param entity_label: Human-readable label for error messages (e.g. "workspace").
    :type entity_label: str
    :return: The resolved ID.
    :rtype: str
    :raises ValueError: If no items exist, or no match / multiple matches found.
    """
    if items is None or items.empty:
        raise ValueError(f"No {entity_label}s found.")

    # Exact ID match
    if value in items[id_column].values:
        return value

    # Substring match on name
    matches = items[items[name_column].str.contains(value, case=False, na=False)]
    if len(matches) == 0:
        available = items[name_column].tolist()
        raise ValueError(
            f"No {entity_label} matching '{value}'. "
            f"Available {entity_label}s: {available}"
        )
    if len(matches) > 1:
        matched = matches[name_column].tolist()
        raise ValueError(
            f"Multiple {entity_label}s matching '{value}': {matched}. "
            f"Please be more specific."
        )
    return matches.iloc[0][id_column]
