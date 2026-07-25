#!/usr/bin/env bash
# Gemma 4 E2B go/no-go for the Encore ID card — one command, macOS.
#
#   ./scripts/gemma_mac_test.sh <clip.wav>
#
# <clip> = an unknown_*.wav from the app container (Xcode > Devices >
# Download Container > AppData/Documents/unknown_clips/), or any 15-30 s
# music excerpt (wav/mp3/flac).
#
# Does everything: installs llama.cpp (brew), downloads the model + BF16
# audio mmproj from Hugging Face (resumable), runs the transcription test
# and the ID-card test on the clip, validates the JSON against
# contracts/id_card.schema.json, prints GO / NO-GO.
set -euo pipefail

CLIP="${1:-}"
[ -f "$CLIP" ] || { echo "usage: $0 <clip.wav>   (unknown_*.wav de l'app, ou 15-30 s de musique)"; exit 1; }

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCHEMA="$REPO_DIR/contracts/id_card.schema.json"
MODELS_DIR="${GEMMA_DIR:-$HOME/models/gemma4}"
HF_REPO="unsloth/gemma-4-E2B-it-GGUF"
MODEL_NAME="gemma-4-E2B-it-UD-Q4_K_XL.gguf"
MMPROJ_NAME="mmproj-BF16.gguf"

echo "── 1/4 llama.cpp"
if ! command -v llama-mtmd-cli >/dev/null 2>&1; then
  brew install llama.cpp
fi

echo "── 2/4 modèle (~2.5 Go au premier run, reprend si interrompu)"
command -v hf >/dev/null 2>&1 || python3 -m pip install -q -U "huggingface_hub[cli]"
mkdir -p "$MODELS_DIR"
hf download "$HF_REPO" --include "*$MODEL_NAME" --include "*$MMPROJ_NAME*" \
  --local-dir "$MODELS_DIR" >/dev/null || {
  echo "Téléchargement refusé — accepte la licence sur https://huggingface.co/$HF_REPO puis: hf auth login"; exit 1; }
MODEL=$(find "$MODELS_DIR" -name "$MODEL_NAME" -type f | head -1)
MMPROJ=$(find "$MODELS_DIR" -name "$MMPROJ_NAME" -type f | head -1)
[ -n "$MODEL" ] && [ -n "$MMPROJ" ] || { echo "fichiers modèle introuvables dans $MODELS_DIR"; exit 1; }

run() { llama-mtmd-cli -m "$MODEL" --mmproj "$MMPROJ" --audio "$CLIP" \
        --temp 1.0 --top-k 64 --top-p 0.95 -ngl 99 --jinja -n 512 -p "$1" 2>/dev/null; }

echo "── 3/4 TEST 1 — transcription (le modèle entend-il les paroles ?)"
run "Transcribe the sung lyrics in this audio exactly. If there are no vocals, describe what you hear in one sentence." | tee /tmp/gemma_t1.txt

echo
echo "── 4/4 TEST 2 — ID card JSON"
run "You listen to a 20 second club recording. Return ONLY a JSON object with keys: genre (string), description (string, one sentence), has_vocals (boolean), confidence (number 0-1), lyrics_snippet (string or null, only include words you clearly hear). Never guess a song title or artist name. No text outside the JSON." | tee /tmp/gemma_t2.txt

echo
python3 - "$SCHEMA" <<'PY'
import json, re, sys, pathlib, subprocess
schema_path = sys.argv[1]
out = pathlib.Path('/tmp/gemma_t2.txt').read_text()
m = re.search(r'\{.*\}', out, re.S)
if not m:
    print("NO-GO ✗ — aucune structure JSON dans la sortie du modèle"); sys.exit(1)
try:
    card = json.loads(m.group(0))
except Exception as e:
    print(f"NO-GO ✗ — JSON invalide: {e}"); sys.exit(1)
card.setdefault("bpm", 128)          # injecté par l'app (DSP), jamais par le modèle
card.setdefault("ts_start_ms", 0)    # idem
try:
    import jsonschema
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "jsonschema"], check=True)
    import jsonschema
try:
    jsonschema.validate(card, json.load(open(schema_path)))
except Exception as e:
    print(f"NO-GO ✗ — l'ID card ne valide pas le schéma: {str(e).splitlines()[0]}"); sys.exit(1)
print("GO ✓ — JSON conforme à contracts/id_card.schema.json")
print("Juge maintenant la QUALITÉ à l'oreille: genre/description cohérents ?"
      " lyrics_snippet correct sur un morceau chanté ?")
PY
