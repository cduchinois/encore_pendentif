import json, pathlib
import jsonschema

ROOT = pathlib.Path(__file__).parents[2]

def test_id_card_schema_is_valid():
    schema = json.loads((ROOT / "contracts/id_card.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)

def test_journal_schema_is_valid():
    schema = json.loads((ROOT / "contracts/journal.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)

def test_example_id_card_validates():
    schema = json.loads((ROOT / "contracts/id_card.schema.json").read_text())
    card = {"genre": "melodic techno", "description": "female vocal hook, driving bassline",
            "has_vocals": True, "confidence": 0.7, "ts_start_ms": 123456}
    jsonschema.validate(card, schema)
