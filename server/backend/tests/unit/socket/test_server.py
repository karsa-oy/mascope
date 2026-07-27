"""
Tests for the socket server's NaN-safe JSON codec.

Python's default JSON encoder renders non-finite floats as the bare literals
``NaN`` / ``Infinity``, which are invalid JSON. The browser's socket.io parser
rejects such a packet with a parse error and drops the connection, so a single
non-finite float in any emitted payload (e.g. a NaN isotope height in an
ion-focus visualization trace) used to kill the client socket. The codec wired
into the socket server must therefore render every payload as strict JSON.
"""

import json

import numpy as np
from socketio import packet as sio_packet

from mascope_backend.socket.server import _NanSafeJson


def strict_loads(payload: str):
    """Parse like a browser's ``JSON.parse``: reject NaN/Infinity literals."""

    def reject(literal):
        raise ValueError(f"non-strict JSON literal: {literal}")

    return json.loads(payload, parse_constant=reject)


class TestNanSafeJson:
    def test_non_finite_floats_render_as_null(self):
        dumped = _NanSafeJson.dumps(
            {"y": [0, float("nan"), float("inf"), float("-inf")]}
        )

        assert strict_loads(dumped) == {"y": [0, None, None, None]}

    def test_numpy_float64_nan_renders_as_null(self):
        # np.float64 is a float subclass; visualization payloads pick them up
        # e.g. from ``np.max`` fallbacks and xarray ``.item()`` calls.
        dumped = _NanSafeJson.dumps({"height": np.float64("nan")})

        assert strict_loads(dumped) == {"height": None}

    def test_nested_containers_are_sanitized(self):
        dumped = _NanSafeJson.dumps(
            {"traces": [{"y": (1.0, float("nan"))}, {"meta": {"e": float("inf")}}]}
        )

        assert strict_loads(dumped) == {
            "traces": [{"y": [1.0, None]}, {"meta": {"e": None}}]
        }

    def test_finite_payloads_pass_through(self):
        payload = {"a": 1, "b": [1.5, "x", None, True], "c": 7e300}

        assert strict_loads(_NanSafeJson.dumps(payload)) == payload

    def test_loads_stays_standard(self):
        assert _NanSafeJson.loads('{"a": 1.5}') == {"a": 1.5}


class TestSocketPacketEncoding:
    def test_emitted_packets_are_strict_json(self):
        # Importing the server module wires the codec into the socket.io packet
        # class, so every emitted packet encodes non-finite floats as null.
        pkt = sio_packet.Packet(
            sio_packet.EVENT,
            data=["visualization_signal_sum_spectrum", {"y": [float("nan")]}],
        )

        encoded = pkt.encode()

        assert "NaN" not in encoded
        assert '"y":[null]' in encoded
