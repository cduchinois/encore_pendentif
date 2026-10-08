#!/usr/bin/env python3
"""Record the pendant's BLE audio (protocol v2) to a WAV, from a Mac.

The BLE smoke test, before touching the iOS app (MVP PRD step 3):

1. Flash the MVP firmware, power the pendant (LED pulses blue = advertising).
2. Close the Encore app on the iPhone (the pendant serves one central at a time).
3. pip install bleak
4. python3 pipeline/tools/ble_listen.py --seconds 60
5. afplay capture.wav, then play it to the Shazam app on another phone.

Gate: < 1 % packet loss and Shazam names the song from the WAV.
"""
import argparse
import asyncio
import time
import wave

from pendant_codec import (AUDIO_SAMPLES, SAMPLE_RATE, SERVICE_UUID, TX_UUID, RX_UUID,
                           cmd_led, parse)


async def run(args):
    try:
        from bleak import BleakClient, BleakScanner
    except ImportError:
        raise SystemExit("bleak missing: pip install bleak")

    print("scanning for the Encore pendant…")
    dev = await BleakScanner.find_device_by_filter(
        lambda d, ad: SERVICE_UUID in [u.lower() for u in ad.service_uuids], timeout=20)
    if dev is None:
        raise SystemExit("no pendant found (powered? already connected to the iPhone?)")
    print(f"found {dev.name} {dev.address}")

    pcm = bytearray()
    stats = {"pkts": 0, "lost": 0, "last_seq": None, "win": 0}

    def on_tx(_, data: bytearray):
        p = parse(bytes(data))
        if p is None:
            print(f"malformed packet type=0x{data[0]:02x} len={len(data)}")
            return
        kind, f = p
        if kind == "audio":
            if stats["last_seq"] is not None:
                gap = (f["seq"] - stats["last_seq"]) & 0xFFFF
                if gap > 1:
                    stats["lost"] += gap - 1
            stats["last_seq"] = f["seq"]
            stats["pkts"] += 1
            stats["win"] += 1
            for s in f["pcm"]:
                pcm.extend(int(s).to_bytes(2, "little", signed=True))
        else:
            print(kind, f)

    async with BleakClient(dev) as client:
        print(f"connected, mtu={client.mtu_size}")
        await client.start_notify(TX_UUID, on_tx)
        await client.write_gatt_char(RX_UUID, cmd_led(2, 0, 60, 0), response=False)  # green pulse
        t0 = time.time()
        try:
            while time.time() - t0 < args.seconds:
                await asyncio.sleep(1)
                total = stats["pkts"] + stats["lost"]
                loss = 100 * stats["lost"] / total if total else 0
                print(f"{stats['win']:4d} pkt/s  loss {loss:.2f} %")
                stats["win"] = 0
        finally:
            await client.write_gatt_char(RX_UUID, cmd_led(0, 0, 0, 0), response=False)

    with wave.open(args.out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(bytes(pcm))
    secs = len(pcm) / 2 / SAMPLE_RATE
    print(f"saved {args.out}: {secs:.1f} s, {stats['pkts']} packets of {AUDIO_SAMPLES} samples, "
          f"{stats['lost']} lost")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--out", default="capture.wav")
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
