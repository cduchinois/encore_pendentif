"""Pendant protocol v2 (BLE) reference: G.711 μ-law codec + TX packet parsing.

Spec: contracts/pendant_protocol.md. The firmware encoder (firmware/src/main.cpp)
and the iOS decoder (ios/Encore/Audio/PendantBLEClient.swift) must stay
bit-identical to these functions; pipeline/tests/test_pendant_protocol.py pins them.
"""
import struct

SERVICE_UUID = "3cfbca53-0d19-4150-acd2-be1d3f437c06"
TX_UUID = "a162065a-4a0f-4fe9-b1b6-eebf575e7b88"
RX_UUID = "ea5ddf58-2e12-4cbe-934e-18d24a0a6cb4"

SAMPLE_RATE = 16000
AUDIO_SAMPLES = 160                    # 10 ms per packet
AUDIO_LEN = 3 + AUDIO_SAMPLES          # type + seq:u16 + ulaw

MSG_EVENT, MSG_HEARTBEAT, MSG_AUDIO_ULAW, MSG_CMD_LED = 0x02, 0x03, 0x04, 0x10
EVENTS = {1: "PIN", 2: "PRIVACY_ON", 3: "PRIVACY_OFF"}

_BIAS, _CLIP = 0x84, 32635


def ulaw_encode(pcm: int) -> int:
    sign = 0x80 if pcm < 0 else 0
    s = min(abs(pcm), _CLIP) + _BIAS
    exponent = 7
    mask = 0x4000
    while exponent > 0 and not (s & mask):
        exponent -= 1
        mask >>= 1
    mantissa = (s >> (exponent + 3)) & 0x0F
    return ~(sign | (exponent << 4) | mantissa) & 0xFF


def ulaw_decode(u: int) -> int:
    u = ~u & 0xFF
    t = (((u & 0x0F) << 3) + _BIAS) << ((u & 0x70) >> 4)
    return _BIAS - t if u & 0x80 else t - _BIAS


_DECODE = [ulaw_decode(i) for i in range(256)]


def parse(packet: bytes):
    """One TX notification -> (kind, fields) or None if malformed."""
    if not packet:
        return None
    t = packet[0]
    if t == MSG_AUDIO_ULAW and len(packet) == AUDIO_LEN:
        (seq,) = struct.unpack_from("<H", packet, 1)
        return "audio", {"seq": seq, "pcm": [_DECODE[b] for b in packet[3:]]}
    if t == MSG_EVENT and len(packet) == 6:
        ts, code = struct.unpack_from("<IB", packet, 1)
        return "event", {"ts_ms": ts, "code": code, "name": EVENTS.get(code, "?")}
    if t == MSG_HEARTBEAT and len(packet) == 3:
        bat, rssi = struct.unpack_from("<Bb", packet, 1)
        return "heartbeat", {"battery_pct": bat, "rssi": rssi}
    return None


def cmd_led(mode: int, r: int, g: int, b: int) -> bytes:
    return bytes([MSG_CMD_LED, mode, r, g, b])
