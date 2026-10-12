# Changelog

## v0.1.1 — 2026-10-12
- Documentation layer completed: README (Problem / How it works / Quickstart / why-not-X anchored on schema-compatibility, task280-regevocompat, schema-evolution lab / Minimal Fallback / Trade-offs / Limits / FAQ), ALIGNMENT.md 16-item audit.
- Self-test re-verified green, no code changes needed this round: `python self_test.py` → `SUMMARY: PASS 69/69`.

## v0.1.0 — 2026-10-11
- Initial implementation: four-level compatibility verdict (FULL/BACKWARD/FORWARD/BREAKING) with worst-wins combination; rules for type sets, enum sets, numeric bounds, required changes, recursive properties/items grading with pointer-style notes, depth-50 recursion cap; CLI (two schema files, `--json`, exit 0/1/2 contract).
- Self-test suite (functional / error / extreme-edge tiers).
