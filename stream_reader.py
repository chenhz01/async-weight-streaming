#!/usr/bin/env python3
"""async-weight-streaming: block-streamed access to files too big to slurp.

Core idea borrowed from inference engines that stream model weights into VRAM
block-by-block instead of loading the whole tensor set: never hold more than
a fixed memory budget, process block-by-block, discard after use.

Pure stdlib. Works on any path or file-like object (so tests can feed in-memory
buffers). Reports peak resident bytes so the budget claim is verifiable.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys

DEFAULT_BLOCK = 1 << 20  # 1 MiB
DEFAULT_MAX_RESIDENT_BLOCKS = 2


class StreamingError(Exception):
    """Protocol violations: lying file-likes, invalid configuration."""


class BlockStream:
    """Iterate a file/file-like in fixed-size blocks under a memory budget.

    The stream never buffers more than ``max_resident_blocks`` blocks at once;
    ``stats()`` reports the observed peak so callers can assert the budget.
    """

    def __init__(self, source, block_size: int = DEFAULT_BLOCK,
                 max_resident_blocks: int = DEFAULT_MAX_RESIDENT_BLOCKS):
        if block_size <= 0:
            raise StreamingError("block_size must be > 0")
        if max_resident_blocks < 1:
            raise StreamingError("max_resident_blocks must be >= 1")
        self._path = source if isinstance(source, str) else None
        self._source = source
        self.block_size = block_size
        self.max_resident_blocks = max_resident_blocks
        self.blocks_read = 0
        self.bytes_total = 0
        self.peak_resident = 0
        self._resident = 0
        self._fh = None

    def _open(self):
        if self._fh is not None:
            return self._fh
        if self._path is not None:
            if not os.path.isfile(self._path):
                raise StreamingError(f"no such file: {self._path}")
            self._fh = open(self._path, "rb")
        else:
            self._fh = self._source
        return self._fh

    def __iter__(self):
        fh = self._open()
        try:
            while True:
                block = fh.read(self.block_size)
                if block is None:
                    break
                if not isinstance(block, (bytes, bytearray)):
                    raise StreamingError("source .read() returned non-bytes")
                if len(block) > self.block_size:
                    raise StreamingError(
                        "source .read(n) returned more than n bytes "
                        f"({len(block)} > {self.block_size}) — lying file-like")
                if not block:
                    break
                self.blocks_read += 1
                self.bytes_total += len(block)
                self._resident = len(block)
                self.peak_resident = max(self.peak_resident, self._resident)
                yield block
                self._resident = 0  # block discarded after consumer is done
        finally:
            if self._path is not None and self._fh is not None:
                self._fh.close()
                self._fh = None

    def stats(self) -> dict:
        return {
            "blocks_read": self.blocks_read,
            "bytes_total": self.bytes_total,
            "peak_resident_bytes": self.peak_resident,
            "block_size": self.block_size,
            "budget_bytes": self.max_resident_blocks * self.block_size,
            "within_budget": self.peak_resident
            <= self.max_resident_blocks * self.block_size,
        }


def stream_sha256(path: str, block_size: int = DEFAULT_BLOCK) -> str:
    """Hash a file without ever loading it whole."""
    h = hashlib.sha256()
    for block in BlockStream(path, block_size):
        h.update(block)
    return h.hexdigest()


def head_bytes(path: str, n: int) -> bytes:
    """Read only the first n bytes (metadata probing without full open-read)."""
    if n < 0:
        raise StreamingError("n must be >= 0")
    with open(path, "rb") as fh:
        return fh.read(n)


def scan(path: str, block_size: int = DEFAULT_BLOCK,
         max_resident_blocks: int = DEFAULT_MAX_RESIDENT_BLOCKS) -> dict:
    """Full pass with stats — the budget assertion in one call."""
    stream = BlockStream(path, block_size, max_resident_blocks)
    for _ in stream:
        pass
    return stream.stats()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="stream_reader",
        description="Block-stream a file under a fixed memory budget.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_stats = sub.add_parser("stats", help="stream whole file, print stats")
    p_stats.add_argument("--file", required=True)
    p_stats.add_argument("--block-size", type=int, default=DEFAULT_BLOCK)
    p_stats.add_argument("--max-resident-blocks", type=int,
                         default=DEFAULT_MAX_RESIDENT_BLOCKS)

    p_hash = sub.add_parser("hash", help="sha256 without full load")
    p_hash.add_argument("--file", required=True)
    p_hash.add_argument("--block-size", type=int, default=DEFAULT_BLOCK)

    p_head = sub.add_parser("head", help="print first n bytes (escaped)")
    p_head.add_argument("--file", required=True)
    p_head.add_argument("--bytes", type=int, default=256)

    args = ap.parse_args(argv)
    try:
        if args.cmd == "stats":
            print(json.dumps(
                scan(args.file, args.block_size, args.max_resident_blocks),
                indent=2))
            return 0
        if args.cmd == "hash":
            print(stream_sha256(args.file, args.block_size))
            return 0
        if args.cmd == "head":
            data = head_bytes(args.file, args.bytes)
            print(repr(data))
            return 0
    except (StreamingError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
