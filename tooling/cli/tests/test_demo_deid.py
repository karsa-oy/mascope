"""
Unit tests for demo raw-file de-identification (``_deidentify_name``).

Pure logic - no infrastructure. Locks in the exact rename transformation.
"""

from mascope_cli.cmd.demo.build_bundle import _deidentify_name


def test_pos_file_renamed():
    name, parsed = _deidentify_name(
        "KORBI2_2025.08.11-14h23m12s_pos_Ur_NoRI_1_20250811142302.raw"
    )
    assert name == "Orbion_pos_Ur_NoRI_20250811142302.raw"
    assert parsed["instrument"] == "KORBI2"
    assert parsed["polarity"] == "pos"
    assert parsed["sample"] == "Ur"
    assert parsed["stamp"] == "20250811142302"


def test_neg_file_renamed():
    name, _ = _deidentify_name(
        "KORBI2_2025.08.11-14h23m58s_neg_Br_NoRI_1_20250811142350.raw"
    )
    assert name == "Orbion_neg_Br_NoRI_20250811142350.raw"


def test_unknown_instrument_kept_with_warning_signal():
    """Unmapped instrument labels are left as-is (caller warns)."""
    name, parsed = _deidentify_name(
        "OTHER_2025.08.11-14h23m12s_pos_Ur_NoRI_1_20250811142302.raw"
    )
    assert name == "OTHER_pos_Ur_NoRI_20250811142302.raw"
    assert parsed["instrument"] == "OTHER"


def test_non_matching_name_unchanged():
    """A name that doesn't fit the pattern is returned unchanged with empty parse."""
    name, parsed = _deidentify_name("something_else.raw")
    assert name == "something_else.raw"
    assert parsed == {}


def test_already_deidentified_is_idempotent():
    """Re-running on an already-renamed file leaves it unchanged but still parses."""
    name, parsed = _deidentify_name("Orbion_pos_Ur_NoRI_20250811142302.raw")
    assert name == "Orbion_pos_Ur_NoRI_20250811142302.raw"
    assert parsed["polarity"] == "pos"
    assert parsed["sample"] == "Ur"
    assert parsed["stamp"] == "20250811142302"
    assert parsed["date"] == "2025.08.11"


def test_custom_alias_map():
    name, _ = _deidentify_name(
        "KORBI2_2025.08.11-14h23m12s_pos_Ur_NoRI_1_20250811142302.raw",
        aliases={"KORBI2": "Demo"},
    )
    assert name == "Demo_pos_Ur_NoRI_20250811142302.raw"
