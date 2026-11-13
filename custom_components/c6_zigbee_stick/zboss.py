"""Minimal ZBOSS NCP client: just enough to recognise an esp-coordinator stick.

No Home Assistant imports here, so the module can be tested on its own.

Wire format (as used by zigbee-herdsman's ZBOSS adapter):

  low level  DE AD | len u16 LE | type 0x06 | flags | crc8(len..flags)
             [crc16(body) u16 LE | body]          (no body in an ACK)
  body       version u8 | type u8 | command u16 LE | tsn u8 | payload
             (a response adds status category u8 and status code u8 before its payload)

len counts everything after the signature. crc8 is CRC-8/KOOP, crc16 is CRC-16/KERMIT.
"""

from __future__ import annotations

from dataclasses import dataclass
import struct
import time

SIGNATURE = b"\xde\xad"
API_HL = 0x06
FLAG_ACK = 0x01
FLAG_FIRST = 0x40
FLAG_LAST = 0x80

FRAME_REQUEST = 0
FRAME_RESPONSE = 1

CMD_GET_MODULE_VERSION = 0x0001


def crc8(data: bytes) -> int:
    """CRC-8/KOOP (poly 0x4D reflected, init 0xFF, xorout 0xFF)."""
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xB2 if crc & 1 else crc >> 1
    return crc ^ 0xFF


def crc16(data: bytes) -> int:
    """CRC-16/KERMIT (poly 0x1021 reflected, init 0)."""
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8408 if crc & 1 else crc >> 1
    return crc


def make_packet(flags: int, body: bytes | None = None) -> bytes:
    """Wrap a high-level body (or nothing, for an ACK) into a low-level packet."""
    length = 5 + (len(body) + 2 if body is not None else 0)
    header = struct.pack("<HBB", length, API_HL, flags)
    packet = SIGNATURE + header + bytes([crc8(header)])
    if body is not None:
        packet += struct.pack("<H", crc16(body)) + body
    return packet


def make_request(command: int, tsn: int, payload: bytes = b"", seq: int = 0) -> bytes:
    """A single-fragment request packet."""
    body = struct.pack("<BBHB", 0, FRAME_REQUEST, command, tsn) + payload
    flags = ((seq & 0x03) << 2) | FLAG_FIRST | FLAG_LAST
    return make_packet(flags, body)


def make_ack(ack_seq: int) -> bytes:
    """ACK for the packet with sequence number ack_seq."""
    return make_packet(((ack_seq & 0x03) << 4) | FLAG_ACK)


@dataclass(frozen=True)
class Packet:
    """One decoded low-level packet."""

    flags: int
    body: bytes  # empty for an ACK

    @property
    def is_ack(self) -> bool:
        return bool(self.flags & FLAG_ACK)

    @property
    def seq(self) -> int:
        return (self.flags >> 2) & 0x03


def parse_packets(buffer: bytearray) -> list[Packet]:
    """Pull every complete, valid packet out of buffer (consumed bytes are removed).

    Garbage before a signature (boot messages, other firmware's logs) is skipped.
    """
    packets: list[Packet] = []
    while True:
        start = buffer.find(SIGNATURE)
        if start < 0:
            # keep a trailing 0xDE: it may be the first half of the next signature
            del buffer[: max(0, len(buffer) - 1)]
            return packets
        del buffer[:start]
        if len(buffer) < 7:
            return packets
        length, ptype, flags, hcrc = struct.unpack_from("<HBBB", buffer, 2)
        if ptype != API_HL or hcrc != crc8(bytes(buffer[2:6])) or length < 5:
            del buffer[:2]  # not a real header, look further
            continue
        total = 2 + length
        if len(buffer) < total:
            return packets
        raw = bytes(buffer[:total])
        del buffer[:total]
        if length == 5:
            packets.append(Packet(flags, b""))
            continue
        (bcrc,) = struct.unpack_from("<H", raw, 7)
        body = raw[9:]
        if bcrc == crc16(body):
            packets.append(Packet(flags, body))


def version_str(value: int) -> str:
    """0x01050050 -> '1.5.0.80' (the format zigbee-herdsman shows)."""
    return ".".join(str((value >> shift) & 0xFF) for shift in (24, 16, 8, 0))


@dataclass(frozen=True)
class ModuleVersion:
    """Answer to GET_MODULE_VERSION."""

    firmware: str
    stack: str
    protocol: str


def parse_module_version(body: bytes, tsn: int | None = None) -> ModuleVersion | None:
    """Decode a GET_MODULE_VERSION response body, or None if body is something else.

    tsn=None accepts an answer to any of our retries.
    """
    if len(body) < 19:
        return None
    _ver, ftype, command, rtsn, _category, status = struct.unpack_from("<BBHBBB", body)
    if ftype != FRAME_RESPONSE or command != CMD_GET_MODULE_VERSION or (tsn is not None and rtsn != tsn) or status != 0:
        return None
    fw, stack, proto = struct.unpack_from("<III", body, 7)
    return ModuleVersion(version_str(fw), version_str(stack), version_str(proto))


def ieee_from_mac(mac: str | None) -> str | None:
    """10:BD:A3:AD:31:A0 -> 0x10bda3fffead31a0 (how the C6 builds its IEEE address)."""
    digits = (mac or "").replace(":", "").lower()
    if len(digits) != 12:
        return None
    return f"0x{digits[:6]}fffe{digits[6:]}"


class PortBusy(Exception):
    """Another program (usually Zigbee2MQTT) holds the port."""


def probe(port: str, timeout: float = 4.0) -> ModuleVersion | None:
    """Ask the device on port for its ZBOSS module version.

    Returns None when the device does not speak ZBOSS (an ESPHome board, a different firmware).
    Raises PortBusy when the port is locked by another program. Blocking: run it in an executor.
    """
    import serial  # pyserial ships with Home Assistant

    ser = serial.Serial()
    ser.port = port
    ser.baudrate = 115200
    ser.timeout = 0.1
    ser.exclusive = True
    # On the ESP32 USB-Serial/JTAG port, RTS high with DTR low resets the chip: keep both low.
    ser.dtr = False
    ser.rts = False
    try:
        ser.open()
    except serial.SerialException as err:
        if "lock" in str(err).lower() or "busy" in str(err).lower():
            raise PortBusy(port) from err
        return None
    try:
        buffer = bytearray()
        deadline = time.monotonic() + timeout
        tsn = 0
        next_send = 0.0
        while time.monotonic() < deadline:
            now = time.monotonic()
            if now >= next_send:  # resend: the chip may have been booting the first time
                tsn = (tsn + 1) & 0xFF
                ser.write(make_request(CMD_GET_MODULE_VERSION, tsn, seq=tsn))
                next_send = now + 1.0
            buffer.extend(ser.read(256))
            for packet in parse_packets(buffer):
                if packet.is_ack or not packet.body:
                    continue
                ser.write(make_ack(packet.seq))
                version = parse_module_version(packet.body)
                if version:
                    return version
        return None
    finally:
        ser.close()
