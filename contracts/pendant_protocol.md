# Pendant <-> iPhone protocol (v1)

Transport: WiFi/UDP primary (iPhone hotspot), BLE fallback. All multi-byte ints little-endian.

## Pendant -> phone
| type | payload | notes |
|---|---|---|
| 0x01 AUDIO | seq:u16, ts_ms:u32, pcm:int16[320] | 16 kHz mono, 20 ms frames |
| 0x02 EVENT | ts_ms:u32, code:u8 | 1=PIN (double tap), 2=PRIVACY_ON, 3=PRIVACY_OFF |
| 0x03 HEARTBEAT | battery_pct:u8, rssi:i8 | every 5 s |

## Phone -> pendant
| type | payload | notes |
|---|---|---|
| 0x10 CMD_LED | mode:u8, r:u8, g:u8, b:u8 | mode 0=off 1=solid 2=pulse 3=flash-once |

Rules: pendant sends nothing while PRIVACY_ON except HEARTBEAT. Phone acks nothing (UDP, fire and forget); loss tolerance is built into recognition (it needs seconds, not every frame).
