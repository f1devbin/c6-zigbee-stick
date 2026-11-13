"""Tests for the ZBOSS framing (no Home Assistant needed)."""

import importlib.util
from pathlib import Path
import struct
import sys

_spec = importlib.util.spec_from_file_location(
    "zboss", Path(__file__).parent.parent / "custom_components/c6_zigbee_stick/zboss.py"
)
zboss = importlib.util.module_from_spec(_spec)
sys.modules["zboss"] = zboss  # dataclasses look the module up while it loads
_spec.loader.exec_module(zboss)

# A real request seen on the wire from zigbee-herdsman (command 0x0014, tsn 1).
REAL_FRAME = bytes.fromhex("dead0c0006c07c7df70000140001")


def test_crc_matches_real_frame():
    assert zboss.crc8(REAL_FRAME[2:6]) == 0x7C
    assert zboss.crc16(REAL_FRAME[9:]) == 0xF77D


def test_make_request_matches_real_frame():
    assert zboss.make_request(0x0014, 1, seq=0) == REAL_FRAME


def test_parse_skips_garbage_and_keeps_partial():
    buf = bytearray(b"ESP-ROM boot\r\n\xde" + REAL_FRAME + REAL_FRAME[:5])
    packets = zboss.parse_packets(buf)
    assert len(packets) == 1
    assert packets[0].body == REAL_FRAME[9:]
    assert bytes(buf) == REAL_FRAME[:5]  # incomplete packet waits for more bytes


def test_parse_rejects_bad_crc():
    bad = bytearray(REAL_FRAME[:-1] + b"\x02")
    assert zboss.parse_packets(bad) == []


def test_ack_roundtrip():
    packets = zboss.parse_packets(bytearray(zboss.make_ack(2)))
    assert len(packets) == 1 and packets[0].is_ack and packets[0].body == b""


def _version_response(tsn=7, status=0):
    body = struct.pack("<BBHBBB", 0, zboss.FRAME_RESPONSE, zboss.CMD_GET_MODULE_VERSION, tsn, 0, status)
    body += struct.pack("<III", 0x01050050, 0x030F0000, 0x00000002)
    return zboss.make_packet(0xC0, body)


def test_module_version_response():
    (packet,) = zboss.parse_packets(bytearray(_version_response()))
    version = zboss.parse_module_version(packet.body)
    assert version == zboss.ModuleVersion("1.5.0.80", "3.15.0.0", "0.0.0.2")
    assert zboss.parse_module_version(packet.body, tsn=8) is None


def test_module_version_error_status():
    (packet,) = zboss.parse_packets(bytearray(_version_response(status=1)))
    assert zboss.parse_module_version(packet.body) is None


def test_ieee_from_mac():
    assert zboss.ieee_from_mac("10:BD:A3:AD:31:A0") == "0x10bda3fffead31a0"
    assert zboss.ieee_from_mac(None) is None
    assert zboss.ieee_from_mac("garbage") is None
