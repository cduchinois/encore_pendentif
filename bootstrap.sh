#!/usr/bin/env bash
# One-time board setup after creating the GitHub repo. Requires: gh auth login.
set -e
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
echo "Bootstrapping $REPO"

# labels
gh label create ios      -c 0A84FF -d "iOS app" -f
gh label create firmware -c FF9F0A -d "XIAO pendant" -f
gh label create pipeline -c 30D158 -d "Python pipeline" -f
gh label create data     -c 64D2FF -d "catalog / demo set" -f
gh label create core     -c FF3B30 -d "demo path — before freeze" -f
gh label create bonus    -c 8E8E93 -d "after freeze only" -f
gh label create context-eng -c BF5AF2 -d "Alien Intelligence track" -f
gh label create demo     -c FFD60A -d "pitch & rehearsal" -f

# milestone
gh api repos/$REPO/milestones -f title="Demo freeze 15h" -f description="Everything core. Not in here = bonus." >/dev/null 2>&1 || true
MS="Demo freeze 15h"

i() { gh issue create -t "$1" -b "$2" $3 --milestone "$MS" >/dev/null && echo "  #$1"; }
ib() { gh issue create -t "$1" -b "$2" $3 >/dev/null && echo "  (bonus) $1"; }

echo "Creating core issues..."
i "fw: UDP audio streaming pendant -> phone" "20ms/16kHz frames per contracts/pendant_protocol.md. Validate with a python listener first." "-l firmware,core"
i "fw: touch gestures (double tap=pin, long press=privacy)" "EVENT codes 1/2/3. Privacy blocks audio, LED off." "-l firmware,core"
i "fw: WS2812B LED (ambiance + pin flash + CMD_LED)" "Modes off/solid/pulse/flash per protocol." "-l firmware,core"
i "ios: UDP receiver + ring buffer + waveform debug view" "Gate 1 (10:30)." "-l ios,core"
i "ios: ShazamKit custom catalog matching" "Load signatures from catalog build; SHCustomCatalog offline match. Gate 2 (12:00)." "-l ios,core"
i "ios: journal + timeline UI" "Per contracts/journal.schema.json. Timeline per demo/dashboard mockup." "-l ios,core"
i "ios: pin event end-to-end" "EVENT(1) -> journal pin -> UI badge -> CMD_LED flash. Gate 3." "-l ios,core"
i "ios: Gemma E2B runner + fiche ID on unknown clip" "Prompt ios/Encore/Gemma/prompts/id_card.md; output MUST validate schema. Gate 3 (13:30)." "-l ios,core"
i "ios: recap generation (Gemma) + energy curve" "Uses compiled party state." "-l ios,core"
i "ios: MusicKit playlist export" "Playlist in Apple Music from journal, pins first. Gate 4 (15:00)." "-l ios,core"
i "pipe: context compiler (party state + SERP evidence)" "pipeline/context/compiler.py, deterministic, tested. Shared shape with Swift." "-l pipeline,context-eng,core"
i "data: golden clips recorded + wired into tests" "The 6 cases in demo/TESTPLAN.md." "-l data,core"
i "demo: rehearse full script x2 + Shazam duel x10" "demo/demo_script.md. Freeze check with verifier agent." "-l demo,core"

echo "Creating bonus issues..."
ib "pipe: SerpAPI live resolver" "Lyrics-quoted search -> evidence -> Gemma arbitration. Cache responses." "-l pipeline,bonus"
ib "pipe: context benchmark (accuracy/token) + chart" "The Alien Intelligence jury artifact." "-l pipeline,context-eng,bonus"
ib "ios: embeddings similarity stage" "Stage 2 of the ladder." "-l ios,bonus"
ib "ios: ShazamKit world catalog stage (online)" "Stage 3 of the ladder." "-l ios,bonus"
ib "ios: background mode (screen off) validation" "BLE accessory background mode." "-l ios,bonus"

echo "Done. Board ready."
