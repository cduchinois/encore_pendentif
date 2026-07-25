#!/usr/bin/env python3
"""Receive pendant AUDIO packets (protocol v1) and record them to a WAV.

The mic smoke test: point the pendant at this machine, speak near it,
then listen to what it heard.

1. Put the Mac on the same iPhone hotspot as the pendant.
2. Find the Mac's IP:            ipconfig getifaddr en0
3. In firmware/src/secrets.h add:  #define ENCORE_PHONE_IP "172.20.10.X"
4. Reflash (pio run -t upload), then run:  python3 pipeline/tools/mic_listen.py
5. Speak / play music near the pendant, Ctrl+C to stop, then:  afplay capture.wav
6. Remove the ENCORE_PHONE_IP line and reflash to point back at the iPhone.

Stdlib only, per the pipeline rules.
"""
import argparse
import socket
import struct
import time
import wave

SAMPLE_RATE = 16000
FRAME_SAMPLES = 320
AUDIO_LEN = 7 + FRAME_SAMPLES * 2  # type + seq:u16 + ts:u32 + pcm


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=7777)
    ap.add_argument("--out", default="capture.wav")
    args = ap.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", args.port))
    sock.settimeout(1.0)
    print(f"listening on 0.0.0.0:{args.port} — Ctrl+C to stop and save {args.out}")

    frames = []
    lost = 0
    last_seq = None
    per_sec = 0
    peak = 0
    t_report = time.time()

    try:
        while True:
            try:
                data, addr = sock.recvfrom(2048)
            except socket.timeout:
                print("waiting for packets… (pendant on? ENCORE_PHONE_IP set to this Mac? same hotspot?)")
                continue
            if not data:
                continue
            if data[0] == 0x01 and len(data) == AUDIO_LEN:
                seq, _ts = struct.unpack_from("<HI", data, 1)
                if last_seq is not None:
                    gap = (seq - last_seq) & 0xFFFF
                    if gap > 1:
                        lost += gap - 1
                last_seq = seq
                pcm = data[7:]
                frames.append(pcm)
                per_sec += 1
                peak = max(peak, max(abs(s[0]) for s in struct.iter_unpack("<h", pcm)))
            elif data[0] == 0x02 and len(data) == 6:
                code = {1: "PIN", 2: "PRIVACY_ON", 3: "PRIVACY_OFF"}.get(data[5], "?")
                print(f"EVENT {code} from {addr[0]}")
            elif data[0] == 0x03 and len(data) == 3:
                battery, rssi = data[1], struct.unpack("b", data[2:3])[0]
                print(f"HEARTBEAT battery={battery}% rssi={rssi} dBm from {addr[0]}")

            now = time.time()
            if now - t_report >= 1.0:
                bar = "#" * int(peak / 32768 * 40)
                print(f"{per_sec:3d} pkt/s (expect ~50)  lost total={lost}  level |{bar:<40}|")
                per_sec = 0
                peak = 0
                t_report = now
    except KeyboardInterrupt:
        pass

    if frames:
        with wave.open(args.out, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            w.writeframes(b"".join(frames))
        print(f"\nsaved {len(frames) * FRAME_SAMPLES / SAMPLE_RATE:.1f} s of audio to {args.out}")
        print(f"listen with:  afplay {args.out}")
    else:
        print("\nno audio received — nothing saved")


if __name__ == "__main__":
    main()
