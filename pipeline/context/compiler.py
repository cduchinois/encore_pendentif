#!/usr/bin/env python3
"""Context compiler — the Alien Intelligence track layer.

Two entry points:
  compile_party_state(journal: dict, budget_tokens: int) -> str
      Rolling, ultra-compact structured state: setlist tail, BPM curve,
      crowd level, pins. Feeds every Gemma call (transitions, moments, recap).
  compile_serp_evidence(serp_json: dict, id_card: dict, budget_tokens: int) -> str
      ~50 KB raw SERP -> <1000 tokens of structured evidence for arbitration.

Both must be deterministic and unit-tested (same input -> same output).
Token counting: len(text) // 4 approximation is fine at the hackathon.
TODO(day-of): implement. The benchmark in bench/context_bench.py consumes these.
"""
