# async-weight-streaming

Read files in fixed-size blocks under a hard memory budget — never slurp the whole thing. A tiny stdlib streaming layer for agent pipelines that touch large files. If your workflow processes multi-megabyte logs, model weights, or OCR sources inside a token/ RAM-limited agent loop, this turns "load then process" into "stream then discard"; if you only handle small config files, keep using plain `open().read()`.

## Problem

The industry reflex for big models used to be "your VRAM must fit the whole model" — until inference engines started streaming weight blocks into memory on demand, decoupling memory footprint from file size. That same decoupling is missing in most agent data pipelines: scripts read entire logs, documents, and downloaded artifacts into one buffer, then wonder why the agent's RAM ceiling and context budget explode.

The overlooked angle: the useful pattern is not "load more" but **use-and-discard** — hold at most N blocks, process, drop, advance. Peak memory becomes a *configurable constant* instead of a function of input size.

## How it works

- `BlockStream(source, block_size, max_resident_blocks)` — iterate any path or file-like in blocks. Each block is yielded and dropped; only one block is resident at a time.
- `stream.stats()` reports `blocks_read`, `bytes_total`, and `peak_resident_bytes`, with an explicit `within_budget` verdict so the memory claim is testable, not aspirational.
- Protocol enforcement: a file-like whose `.read(n)` returns more than `n` bytes raises `StreamingError` — lying sources are caught, not silently trusted.
- Helpers: `stream_sha256(path)` (hash without full load), `head_bytes(path, n)` (metadata probing), `scan(path)` (full pass with stats).

Quickstart (~5 min):

```bash
# 1. Self-test (~10 s)
python self_test.py

# 2. Stream stats for any file (~2 s for 10 MiB)
python stream_reader.py stats --file big.log --block-size 262144
# -> {"blocks_read": 40, "peak_resident_bytes": 262144, "within_budget": true, ...}

# 3. Hash a huge file without loading it (~3 s per 100 MiB, disk-bound)
python stream_reader.py hash --file weights.bin

# 4. Peek at the head only
python stream_reader.py head --file model.safetensors --bytes 64
```

## Why not X

| Alternative | Why not |
|---|---|
| `path.read()` then process | Peak memory scales with input size; a 2 GiB log is a 2 GiB buffer. Streaming caps it at `block_size` regardless. |
| `mmap` | Zero-copy, but still maps the *whole* file into address space, fails on some network filesystems, and gives you no block-level stats or protocol checks. |
| External chunkers (`split` + shell loop) | Spawns processes and re-parses per chunk; no single stats object, no budget assertion, awkward inside a Python agent loop. |
| pandas/polars batch readers | Heavier dependency, schema assumptions, and overkill for byte-level pipelines (hashing, scanning, OCR feeding). |

## Minimal Fallback

No Python? The pattern collapses to shell and still works:

```bash
# 4 MiB blocks, hash without full load — same discipline, zero Python
split -b 4194304 big.bin part_ && cat part_* | sha256sum && rm part_*
```

Or in Python without this repo: `hashlib.file_digest(open(p,'rb'), hashlib.sha256)` covers hashing only; you lose the budget stats and the lying-file-like detection.

## Design Trade-offs

Priorities: **memory bound > correctness > simplicity > throughput.**

- One-block-resident is conservative: a lookahead/prefetch buffer would raise throughput but break the "peak = one block" invariant that makes the budget claim testable.
- Raising `StreamingError` on protocol-violating file-likes trades convenience for catching real corruption early.
- No async/threading despite the name heritage: the value is the *streaming discipline*, not concurrency; a generator composes with any executor you already have.

## Limits & Second-order Effects

- Disk-bound: streaming is slower than one big `read()` for small files (syscall overhead). Below ~1 MiB, just slurp.
- Adoption side effect: pipelines that always stream may develop **invisible truncation bugs** — a consumer that breaks out of the loop early sees a prefix and can mistake it for the whole file. Always check `stats()["bytes_total"]` against expectations.
- Streaming makes huge inputs *feasible*, which invites unbounded processing: a memory budget does not replace a time budget. Pair with a block-count cap for adversarial inputs.

## FAQ

**Is this actually async?**
No — the name honors the inference-engine pattern it borrows. It is a synchronous generator; wrap it in your own executor if you need overlap.

**When should you NOT use this tool?**
Files under a few MiB, or cases where you need random access throughout (streaming is sequential). Also not a substitute for a database when you need indexed queries.

**How do I prove the memory claim on my machine?**
`python self_test.py` — the "peak resident within budget" test asserts `peak_resident_bytes <= 2 * block_size` on a 3 MiB and a 10 MiB input.

## Core Assumptions

1. Sequential access covers the target workloads (hashing, scanning, feeding models/OCR) — random-access workloads are out of scope.
2. `file.read(n)` obeying its contract (≤ n bytes) is a fair assumption to enforce, not just hope for.
3. Peak-resident accounting at the Python-object level (one block buffer) is the right proxy for process memory for single-stream use.
4. Consumer code holds no references to yielded blocks after the next iteration.

Confidence: **High** that block streaming caps peak memory independent of file size (proven by self-test assertions, reproducible via `python self_test.py`). Confidence: **Medium** that agent pipelines see meaningful RAM relief in practice — plausible from the mechanism, but no external benchmark yet [estimated].

Performance figures in Quickstart (10 MiB ≈ 2 s, hashing ≈ disk-bound): measured informally during development; treat as [estimated] until you run `self_test.py` on your hardware.

Source inspiration (structural restatement only): https://github.com/Comfy-Org/ComfyUI — streaming weight loading in a node-based diffusion backend.

Time-sensitive notes: **as of 2026-10-11**.

License: MIT. Contact: hcac4735@agent.qq.com
