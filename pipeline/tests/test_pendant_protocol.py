import json, pathlib, struct, sys
import jsonschema

ROOT = pathlib.Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "tools"))
import pendant_codec as pc  # noqa: E402


def test_ulaw_reference_points():
    # Classic G.711 values: silence, full scale, the decoder's extremes.
    assert pc.ulaw_encode(0) == 0xFF
    assert pc.ulaw_decode(0xFF) == 0
    assert pc.ulaw_encode(32767) == 0x80
    assert pc.ulaw_encode(-32768) == 0x00
    assert pc.ulaw_decode(0x80) == 32124
    assert pc.ulaw_decode(0x00) == -32124


def test_ulaw_roundtrip_error_is_bounded():
    for x in range(-32768, 32768, 7):
        y = pc.ulaw_decode(pc.ulaw_encode(x))
        # μ-law step is at most 1024 at the top segment; relative error < ~6 %.
        assert abs(y - x) <= max(16, abs(x) // 16 + 1) or abs(x) > 32124


def test_ulaw_is_monotonic():
    decoded = [pc.ulaw_decode(pc.ulaw_encode(x)) for x in range(-32768, 32768, 64)]
    assert decoded == sorted(decoded)


def test_parse_packets():
    audio = bytes([0x04]) + struct.pack("<H", 513) + bytes([0xFF] * pc.AUDIO_SAMPLES)
    kind, f = pc.parse(audio)
    assert kind == "audio" and f["seq"] == 513 and f["pcm"] == [0] * pc.AUDIO_SAMPLES
    assert len(audio) <= 182, "must fit the ATT MTU iOS negotiates (185 - 3)"
    assert pc.parse(bytes([0x02]) + struct.pack("<IB", 1234, 1)) == (
        "event", {"ts_ms": 1234, "code": 1, "name": "PIN"})
    assert pc.parse(bytes([0x03, 87, 0])) == ("heartbeat", {"battery_pct": 87, "rssi": 0})
    assert pc.parse(bytes([0x04, 0, 0])) is None
    assert pc.cmd_led(3, 80, 0, 255) == bytes([0x10, 3, 80, 0, 255])


def test_protocol_doc_matches_codec_constants():
    doc = (ROOT / "contracts/pendant_protocol.md").read_text()
    for uuid in (pc.SERVICE_UUID, pc.TX_UUID, pc.RX_UUID):
        assert uuid in doc


def test_example_cloud_journal_validates():
    schema = json.loads((ROOT / "contracts/journal.schema.json").read_text())
    id_card = json.loads((ROOT / "contracts/id_card.schema.json").read_text())
    from referencing import Registry, Resource
    registry = Registry().with_resource("id_card.schema.json", Resource.from_contents(id_card))
    track = {"shazam_id": "1440841746", "title": "Blue Monday", "artist": "New Order",
             "isrc": "GBAAP9800007", "apple_music_id": "1440841760",
             "artwork_url": "https://is1-ssl.mzstatic.com/image/x.jpg",
             "apple_music_url": None}
    journal = {"session_id": "s1", "started_at": "2026-10-08T22:00:00Z", "events": [
        {"ts_ms": 12000, "kind": "track_match", "track_id": None, "source": "world_catalog", "track": track},
        {"ts_ms": 30000, "kind": "pin", "track": track},
        {"ts_ms": 90000, "kind": "track_match", "source": "world_catalog", "note": "offline"},
    ]}
    jsonschema.Draft202012Validator(schema, registry=registry).validate(journal)
