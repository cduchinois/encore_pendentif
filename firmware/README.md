# firmware/ — the pendant (XIAO ESP32-S3 Sense)

[← Main README](../README.md) · Protocol: [contracts/pendant_protocol.md](../contracts/pendant_protocol.md) · Wiring: [hardware/wiring.md](../hardware/wiring.md) · Owner: firmware-dev agent

The pendant is a **smart microphone, nothing more** (decision log: nothing pendant-sized runs Gemma E2B). It captures PDM audio, streams 20 ms frames over UDP to the iPhone hotspot, reports touch gestures, and drives one WS2812B LED. All packet formats come from the protocol contract — keep them in sync.

## How it works

- **Capture**: on-board PDM mic (CLK=GPIO42, DATA=GPIO41) via I2S at 16 kHz mono, 320-sample (20 ms) frames.
- **Streaming**: each frame is packed as an `AUDIO` packet (`0x01` + seq + ts_ms + PCM, 647 bytes) and fired at the iPhone hotspot gateway (`172.20.10.1:7777`), no acks — loss tolerance is built into recognition.
- **Touch** (copper pad → GPIO1/T1): double tap (~400 ms window) = pin → `EVENT` code 1; long press (>1.2 s) = privacy toggle → `EVENT` 2/3. Privacy mode stops all audio; only heartbeats continue.
- **LED** (WS2812B on GPIO2): ambiance color / pulse / white flash on pin, driven by incoming `CMD_LED` (`0x10`) packets from the phone. Privacy = LED off, unambiguous.
- **Heartbeat**: battery % + RSSI every 5 s.

## Build & flash

```bash
cd firmware
pio run -t upload      # XIAO ESP32-S3 plugged in over USB-C
pio device monitor     # 115200 baud
```

Set `WIFI_SSID` / `WIFI_PASS` in `src/main.cpp` to the iPhone hotspot before flashing. Validate streaming with a quick Python UDP listener before touching the app (that's the plan's "BIGGEST RISK — do this first").

## Status

**Working** (`src/main.cpp`): mic setup, frame capture loop, AUDIO + EVENT packet packing (byte-for-byte per contract), WiFi connect, LED init.

**TODO (day-of, declared in main.cpp)**:
- [ ] Touch gesture detection (double tap window ~400 ms, long press >1.2 s) wired to `EVENT` + `privacyMode`.
- [ ] Receive path for `CMD_LED` (`udp.parsePacket()`) → ambiance color / pulse / pin flash.
- [ ] HEARTBEAT every 5 s with battery estimate.

**Hardening worth doing before gate 1**:
- [ ] `WiFi.setSleep(false)` — modem power-save causes UDP jitter, the classic cause of choppy audio streaming.
- [ ] Bounded WiFi connect retry + error LED color (currently blocks forever on a dead hotspot).
- [ ] Host-side `pio test`: frame pack/unpack round-trip against the protocol doc (see `test/README.md` — keep protocol logic in pure functions).

## Hardware notes

Pins match [hardware/wiring.md](../hardware/wiring.md). Power: LiPo 500–600 mAh on the BAT pads (on-board charging) or a mini USB-C power bank inside the case. Battery target: survive 1 h of streaming (test plan).
