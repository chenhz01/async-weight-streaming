# Changelog

## v0.1.1 — 2026-10-11 (self-review revision, iteration 2)

### Improved (readability/correctness dimension)
- Removed a dead code fragment in `self_test.py` edge tests left from an
  abandoned assertion draft (clarity pass; file now has zero dead branches).
- README: every performance figure now explicitly labeled (self-test-backed
  or [estimated]) — before the revision, two informal timings were presented
  without a source tag. Fixes ALIGNMENT rule 4 gap found in self-review.
- README "Limits" gained a concrete second-order failure mode: silent
  truncation when a consumer breaks out of the stream early, with the
  `bytes_total` check as the countermeasure.

## v0.1.0 — 2026-10-11 (initial draft)

- `BlockStream`: block iterator with peak-resident accounting and
  `max_resident_blocks` budget.
- Protocol enforcement for lying file-likes (`.read(n)` > n → `StreamingError`).
- Helpers: `stream_sha256`, `head_bytes`, `scan`.
- CLI: `stats` / `hash` / `head` (argparse).
- `self_test.py`: 13 tests across functional / error-path / extreme-edge
  (empty file, 10 MiB file, truncated stream, exact-block-size file) — 13/13 PASS.
- README, LICENSE (MIT), initial alignment audit.
