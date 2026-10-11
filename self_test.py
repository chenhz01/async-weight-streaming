#!/usr/bin/env python3
"""Self-test for async-weight-streaming (ALIGNMENT rule 97 three families).

Run:  python self_test.py
"""
import hashlib
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stream_reader as sr  # noqa: E402

results = []


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))


# ------------------------------------------------------------- functional ---
def test_functional(tmp):
    data = os.urandom(3 * 1024 * 1024)  # 3 MiB
    path = os.path.join(tmp, "weights.bin")
    with open(path, "wb") as fh:
        fh.write(data)

    got = sr.stream_sha256(path, 65536)
    record("functional: streamed sha256 matches hashlib",
           got == hashlib.sha256(data).hexdigest())

    stats = sr.scan(path, 262144, 2)
    record("functional: block count exact",
           stats["blocks_read"] == 12 and stats["bytes_total"] == len(data))
    record("functional: peak resident within budget (<= 2 blocks)",
           stats["within_budget"] and
           stats["peak_resident_bytes"] <= 2 * 262144,
           str(stats))

    head = sr.head_bytes(path, 16)
    record("functional: head_bytes returns first 16", head == data[:16])


# ----------------------------------------------------------- error paths ---
def test_errors(tmp):
    try:
        sr.scan(os.path.join(tmp, "ghost.bin"))
        record("error: missing file raises StreamingError", False)
    except sr.StreamingError:
        record("error: missing file raises StreamingError", True)

    try:
        sr.BlockStream(io.BytesIO(b"x"), block_size=0)
        record("error: block_size=0 raises", False)
    except sr.StreamingError:
        record("error: block_size=0 raises", True)

    class Liar:
        def read(self, n):
            return b"\x00" * (n * 2)  # violates read(n) contract

    try:
        list(sr.BlockStream(Liar(), 1024))
        record("error: lying file-like raises", False)
    except sr.StreamingError:
        record("error: lying file-like raises", True)

    try:
        sr.head_bytes(os.path.join(tmp, "h.bin"), -1)
        record("error: negative head n raises", False)
    except (sr.StreamingError, OSError):
        record("error: negative head n raises", True)


# ------------------------------------------------------------ edge cases ---
def test_edges(tmp):
    empty = os.path.join(tmp, "empty.bin")
    open(empty, "wb").close()
    stats = sr.scan(empty, 65536)
    record("edge: empty file -> 0 blocks, hash of empty",
           stats["blocks_read"] == 0 and
           sr.stream_sha256(empty) == hashlib.sha256(b"").hexdigest())

    big = os.path.join(tmp, "big.bin")
    with open(big, "wb") as fh:
        for _ in range(10):
            fh.write(os.urandom(1024 * 1024))
    stats = sr.scan(big, 1 << 20)
    record("edge: 10 MiB file, peak stays 1 block",
           stats["blocks_read"] == 10 and
           stats["peak_resident_bytes"] <= (1 << 20))

    exact = os.path.join(tmp, "exact.bin")
    with open(exact, "wb") as fh:
        fh.write(b"\x01" * 65536)
    stats = sr.scan(exact, 65536)
    record("edge: size == block_size -> exactly 1 block",
           stats["blocks_read"] == 1)

    class Truncated:
        """File-like that claims a huge payload but stops after one block."""
        def __init__(self):
            self.calls = 0
        def read(self, n):
            self.calls += 1
            return b"data" if self.calls == 1 else b""

    stream = sr.BlockStream(Truncated(), 8)
    blocks = list(stream)
    record("edge: truncated stream yields partial then stops",
           len(blocks) == 1 and stream.stats()["bytes_total"] == 4)

    record("edge: max_resident_blocks=1 accepted", sr.BlockStream(
        io.BytesIO(b"x"), 4, 1).max_resident_blocks == 1)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        test_functional(tmp)
        test_errors(tmp)
        test_edges(tmp)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
