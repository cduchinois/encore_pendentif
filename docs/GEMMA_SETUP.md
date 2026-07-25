# Gemma 4 E2B — model choice & setup guide

Which Hugging Face artifacts to download, how to test them on the Mac tonight, and how
they land in the iOS app. Companion to `PLAN.md` (day-before item: "Gemma E2B running on
Mac AND iPhone, llama.cpp vs AI Edge, keep the winner").

## Which model

**`google/gemma-4-E2B-it`** — nothing else.

- **E2B**, not the 12B/26B/31B that come up first when searching "gemma" on HF: those
  don't fit an iPhone and the big ones drop native audio input. E2B is the edge variant:
  native audio in, ~2 GB RAM footprint (see `DECISIONS.md` 2026-07-22), function calling
  and structured JSON output — exactly what the ID card, transitions and recap need.
- **`-it`** (instruction-tuned), never the base `google/gemma-4-E2B`: we prompt it, we
  don't fine-tune it.
- Ignore community fine-tunes (`yuxinlu1/...`, `HauhauCS/...`): unknown behavior, no
  audio guarantees, and the jury track is Gemma 4 as shipped.

We never load the raw `google/` checkpoint on-device — we use converted artifacts, one
per candidate runtime:

| Runtime | HF repo | Files |
|---|---|---|
| llama.cpp | `ggml-org/gemma-4-E2B-it-GGUF` | `gemma-4-E2B-it-Q4_K_M.gguf` (~3.1 GB) **+ `mmproj-BF16.gguf`** |
| Google AI Edge (LiteRT-LM / MediaPipe) | `litert-community/gemma-4-E2B-it-litert-lm` | the `.litertlm` bundle |

Pitfalls learned from the field:

- **The mmproj file is mandatory for audio** in llama.cpp — without it Gemma is
  text-only and the ID card stage is dead. Use the **BF16** mmproj: the combined
  vision+audio projector doesn't survive K-quant (Q6_K aborts).
- Prefer `ggml-org`'s GGUFs; some `unsloth` mmproj builds shipped without the audio
  encoder (see the discussion thread on their repo).
- llama.cpp audio works through **libmtmd / `llama-mtmd-cli`**, not `llama-server`
  (the server has no `input_audio` route). On iOS we bind libmtmd directly, so this
  only matters for Mac testing — use the CLI, not the server.

## Download

1. Accept the Gemma license once on the `google/gemma-4-E2B-it` model page (HF account
   required; the gate propagates to the converted repos).
2. ```bash
   pip install -U "huggingface_hub[cli]"
   hf auth login   # paste a read token from huggingface.co/settings/tokens

   # Track A — llama.cpp
   hf download ggml-org/gemma-4-E2B-it-GGUF gemma-4-E2B-it-Q4_K_M.gguf --local-dir data/models
   hf download ggml-org/gemma-4-E2B-it-GGUF mmproj-BF16.gguf          --local-dir data/models

   # Track B — Google AI Edge
   hf download litert-community/gemma-4-E2B-it-litert-lm --local-dir data/models/litert
   ```
3. `data/` is gitignored — model weights never enter git. They reach the iPhone as Xcode
   app resources (see `ios/README.md`, `Gemma/LlamaRunner.swift`).

## Mac smoke test (tonight)

Goal: prove audio-in works and pick numbers to compare, ~30 min total.

```bash
brew install llama.cpp   # or build from source for latest mtmd fixes

llama-mtmd-cli \
  -m data/models/gemma-4-E2B-it-Q4_K_M.gguf \
  --mmproj data/models/mmproj-BF16.gguf \
  --audio data/samples/unknown_clip.wav \
  -p "Listen to this club recording. Return ONLY a JSON object with keys: genre, description, has_vocals, confidence, ts_start_ms, lyrics_snippet. Do not guess a BPM."
```

For Track B, run the same clip through the LiteRT-LM CLI (or the MediaPipe LLM
Inference sample app) with the `.litertlm` bundle.

Record for each runtime: audio actually understood (y/n), tokens/s, peak RAM, and
whether the output parses against `contracts/id_card.schema.json`.

## Picking the winner

- llama.cpp path on iOS: llama.cpp Swift package, GGUF + mmproj in app resources,
  libmtmd for the audio path.
- AI Edge path on iOS: MediaPipe LLM Inference pod / LiteRT-LM, `.litertlm` in app
  resources. Google's stack is moving to LiteRT-LM (classic MediaPipe LLM API is
  maintenance-only), so prefer LiteRT-LM if both work.

Decide on: audio-in reliability first, then tokens/s on the actual iPhone, then RAM
headroom next to ShazamKit + the audio receiver. Write the winner as one line in
`DECISIONS.md` and move on — the runner lives behind `Gemma/LlamaRunner.swift` either
way, so the loser stays swappable.
