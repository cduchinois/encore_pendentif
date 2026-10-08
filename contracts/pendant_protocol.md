# Pendant <-> iPhone protocol (v2, BLE)

Transport: Bluetooth Low Energy. The pendant is a GATT peripheral, the iPhone the central.
v1 (WiFi hotspot + UDP :7777, raw PCM) lives on `main`; v2 replaces it on the `MVP` branch.
All multi-byte ints little-endian.

## GATT

| item | UUID | properties |
|---|---|---|
| Encore service | `3cfbca53-0d19-4150-acd2-be1d3f437c06` | advertised, device name `Encore` |
| TX (pendant -> phone) | `a162065a-4a0f-4fe9-b1b6-eebf575e7b88` | notify |
| RX (phone -> pendant) | `ea5ddf58-2e12-4cbe-934e-18d24a0a6cb4` | write, write without response |

Every TX notification and every RX write is exactly one packet; byte 0 is the type.
Largest packet is 163 bytes, so it fits the ATT MTU iOS (and bleak on macOS) negotiates at connect (185, payload 182). A central that stays at the BLE default MTU of 23 would get truncated packets.

## Pendant -> phone (TX notify)
| type | payload | notes |
|---|---|---|
| 0x04 AUDIO_ULAW | seq:u16, ulaw:u8[160] | 16 kHz mono, 10 ms per packet (100 packets/s), G.711 μ-law |
| 0x02 EVENT | ts_ms:u32, code:u8 | 1=PIN (double tap), 2=PRIVACY_ON, 3=PRIVACY_OFF |
| 0x03 HEARTBEAT | battery_pct:u8, rssi:i8 | every 5 s; rssi is 0 over BLE (the phone reads RSSI itself) |

`seq` increments by 1 per AUDIO_ULAW packet and wraps at 65535; the phone uses gaps to count loss.

## Phone -> pendant (RX write)
| type | payload | notes |
|---|---|---|
| 0x10 CMD_LED | mode:u8, r:u8, g:u8, b:u8 | mode 0=off 1=solid 2=pulse 3=flash-once |

## μ-law (G.711)

Encoder (pendant) and decoders (iOS, Python) must stay bit-identical to this reference:

```
encode(pcm: int16) -> u8:
  sign = 0x80 if pcm < 0 else 0;  s = min(|pcm|, 32635) + 0x84
  exponent = index of highest set bit of s among bits 14..7, minus 7 (0..7)
  mantissa = (s >> (exponent + 3)) & 0x0F
  return ~(sign | exponent << 4 | mantissa) & 0xFF

decode(u: u8) -> int16:
  u = ~u;  t = ((u & 0x0F) << 3) + 0x84;  t <<= (u & 0x70) >> 4
  return (0x84 - t) if (u & 0x80) else (t - 0x84)
```

Reference implementation and tests: `pipeline/tools/pendant_codec.py`, `pipeline/tests/test_pendant_protocol.py`.

## Rules
- The pendant streams AUDIO_ULAW only while a central is subscribed to TX; otherwise it advertises and pulses the LED blue.
- The pendant sends nothing while PRIVACY_ON except HEARTBEAT.
- The pendant requests a 15 to 30 ms connection interval after connect (Apple accessory guidelines).
- No acks. Loss tolerance is built into recognition (it needs seconds, not every packet).
