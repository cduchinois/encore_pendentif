#!/usr/bin/env python3
"""Accuracy-per-token benchmark for the jury (Alien Intelligence track).

Cases: N resolution tasks with known ground truth (track really is X).
Arms: A) small model + compile_serp_evidence()  B) big model + raw SERP JSON.
Metric: correct resolutions / context tokens spent. Output: one table + one chart.
TODO(day-of): implement with 10-20 cases from the demo set.
"""
