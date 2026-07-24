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

First time on a new machine:

```bash
pip install platformio                      # or the VSCode PlatformIO extension
cd firmware
cp src/secrets.h.example src/secrets.h      # then fill in the hotspot SSID/password
```

`secrets.h` is gitignored — credentials never land in git.

Every flash:

```bash
cd firmware
pio run                # compile only (optional sanity check)
pio run -t upload      # compile + flash, XIAO plugged in over USB-C, port auto-detected
pio device monitor     # serial console, 115200 baud (Ctrl+C to quit)
```

If upload fails ("failed to connect"): hold **BOOT**, press **RESET**, release RESET, release BOOT, then `pio run -t upload` again. Same esptool underneath as `idf.py flash`.

Expected boot log on the monitor:

```
connecting to "encore-hotspot"......
wifi ok — pendant ip 172.20.10.2, rssi -48 dBm
streaming AUDIO -> 172.20.10.1:7777 (16 kHz mono, 20 ms frames)
touch baseline 24817
ready — double tap = PIN, long press = privacy toggle
```

Endless dots + blinking blue→red LED = can't join the hotspot: check it's ON, creds match `secrets.h`, and **"Maximize Compatibility" is enabled** on the iPhone (the XIAO is 2.4 GHz only).

Validate streaming with a quick Python UDP listener before touching the app (that's the plan's "BIGGEST RISK — do this first"):

```bash
python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(('0.0.0.0', 7777))
while True:
    d, a = s.recvfrom(2048)
    print(f'{a[0]} type=0x{d[0]:02x} len={len(d)}')"
```

(Run it on a Mac on the same hotspot; point `PHONE_IP` at the Mac's IP temporarily, or just trust the phone path.)

## Status

**Working** (`src/main.cpp`): mic capture at 16 kHz → AUDIO frames over UDP, touch gestures (double tap = PIN, long press = privacy toggle), CMD_LED receive path (solid/pulse/flash-once), HEARTBEAT every 5 s (RSSI real, battery stubbed at 100), `WiFi.setSleep(false)`, auto-reconnect on WiFi loss, boot log with IP.

**TODO**:
- [ ] Real battery % — needs a voltage divider from BAT+ to an ADC pin (hardware decision, not blocking).
- [ ] Tune `touchBaseline` threshold on the real copper pad (baseline is auto-calibrated at boot; factor is 1.5×).
- [ ] Host-side `pio test`: frame pack/unpack round-trip against the protocol doc (see `test/README.md` — keep protocol logic in pure functions).

## Hardware notes

Pins match [hardware/wiring.md](../hardware/wiring.md). Power: LiPo 500–600 mAh on the BAT pads (on-board charging) or a mini USB-C power bank inside the case. Battery target: survive 1 h of streaming (test plan).
