#!/usr/bin/env python3
"""Deferred resolution of unknown tracks via SerpAPI.

Input: an id_card JSON (contracts/id_card.schema.json) + saved clip path.
Steps: 1) Google search of quoted lyrics_snippet  2) description search
       3) YouTube results check  4) compile evidence (context/compiler.py)
       5) Gemma arbitration -> candidate + confidence.
Cache every SerpAPI response in data/serp_cache/<hash>.json (credits!).
TODO(day-of): implement; keep each step a pure function with fixture tests.
"""
