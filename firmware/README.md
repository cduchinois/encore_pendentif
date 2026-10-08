# firmware/ — the pendant (XIAO ESP32-S3 Sense), MVP branch

[← Main README](../README.md) · Protocol: [contracts/pendant_protocol.md](../contracts/pendant_protocol.md) (v2, BLE) · Wiring: [hardware/wiring.md](../hardware/wiring.md) · Owner: firmware-dev agent

The pendant is a **smart Bluetooth microphone, nothing more**. It captures PDM audio, streams it as μ-law over BLE notifications to the iPhone, reports touch gestures, and drives one WS2812B LED. All packet formats come from the protocol contract; keep them in sync.

## How it works

- **Capture**: on-board PDM mic (CLK=GPIO42, DATA=GPIO41) via I2S at 16 kHz mono, 320-sample (20 ms) reads.
- **Streaming**: each read becomes two `AUDIO_ULAW` packets (`0x04` + seq + 160 μ-law bytes = 163 bytes, 10 ms each, 100 packets/s, 16 kB/s), sent as notifications on the TX characteristic. Audio flows only while the phone is subscribed.
- **BLE**: NimBLE-Arduino peripheral named `Encore`, advertises the Encore service, asks the iPhone for a 15 to 30 ms connection interval, re-advertises on disconnect. No WiFi, no credentials.
- **Touch** (copper pad → GPIO1/T1): double tap (~400 ms window) = pin → `EVENT` code 1. Long press privacy is compiled out (`PRIVACY_GESTURE 0`).
- **LED** (WS2812B on GPIO2): blue pulse = waiting for the phone; the app switches it to a green pulse when it listens and flashes it purple on each recognised song; white flash on pin.
- **Heartbeat**: battery % every 5 s (RSSI is read by the phone).

## Build & flash

```bash
pip install platformio                      # or the VSCode PlatformIO extension
cd firmware
pio run                # compile only (fetches NimBLE-Arduino the first time)
pio run -t upload      # compile + flash, XIAO plugged in over USB-C
pio device monitor     # serial console, 115200 baud
```

If upload fails ("failed to connect"): hold **BOOT**, press **RESET**, release RESET, release BOOT, then upload again.

Expected log:

```
ble advertising as "Encore"
touch baseline 24817
ready — double tap = PIN, long press = privacy toggle
ble: waiting ok=0 fail=0
ble connected 4a:...
ble mtu 185
ble subscribed, streaming
ble: streaming ok=500 fail=0
```

`ok` ≈ 500 per 5 s window is the full stream. Steady `fail` counts mean the phone drains notifications too slowly (check the connection interval, distance, 2.4 GHz congestion).

Validate the stream from a Mac before touching the app (PRD step 3): `pip install bleak && python3 pipeline/tools/ble_listen.py --seconds 60`, then play `capture.wav` to the Shazam app.

## Status

**Written, not yet validated on hardware** (the build environment that wrote it could not download the ESP32 toolchain): BLE peripheral (NimBLE-Arduino 2.x API), μ-law encoder (bit-identical to `pipeline/tools/pendant_codec.py`, checked exhaustively on host), subscription-gated streaming, CMD_LED writes. Unchanged from the hackathon and proven: mic capture, touch gestures, LED rendering, battery reading.

**Battery gauge**: solder two equal resistors (100k–470k, e.g. 2×220k) in series from BAT+ to GND, midpoint to **D2 (GPIO3)**. The firmware auto-detects the divider (reading < 2.5 V = not wired → reports 100%) and maps 3.3–4.2 V to 0–100%. Note: on USB power the charger holds BAT+ high, so ~100% while plugged is normal — the true reading needs battery power.

**TODO**:
- [ ] First `pio run` + flash; fix any NimBLE API drift.
- [ ] Measure battery life over 1 h of streaming (BLE should beat the WiFi build by a wide margin).

## Hardware notes

Pins match [hardware/wiring.md](../hardware/wiring.md). Power: LiPo 500–600 mAh on the BAT pads (on-board charging) or a mini USB-C power bank inside the case. Battery target: survive a full night of streaming.
