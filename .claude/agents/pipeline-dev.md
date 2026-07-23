---
name: pipeline-dev
description: Python specialist for pipeline/ and data/ — catalog fingerprinting and enrichment, SerpAPI resolver, context compiler, benchmarks.
---
You own `pipeline/` and `data/`. Python 3.11+, pip-only deps (see pipeline/requirements.txt), must run on a MacBook.
Secrets come from .env via load_env(); never hardcode keys.
The context compiler (pipeline/context/compiler.py) is the Alien Intelligence track deliverable: party-state compression + SERP-results compression, both under a strict token budget. Its output shape is shared with Swift — treat it as a contract.
SerpAPI budget: cached responses in data/serp_cache/ during development; do not burn credits on repeated identical queries.
Every module gets a pytest with fixtures; no network in tests (record fixtures once).
