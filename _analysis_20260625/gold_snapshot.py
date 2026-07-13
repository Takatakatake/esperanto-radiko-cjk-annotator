# -*- coding: utf-8 -*-
"""Consistent, read-only snapshots for the externally synchronized gold file."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")


def consistent_snapshot(path, attempts=20, retry_seconds=0.1):
    """Read bytes only when size/mtime remain identical around the read."""
    path = Path(path)
    for _attempt in range(attempts):
        before = path.stat()
        raw = path.read_bytes()
        after = path.stat()
        before_id = (before.st_size, before.st_mtime_ns)
        after_id = (after.st_size, after.st_mtime_ns)
        if before_id == after_id and len(raw) == after.st_size:
            return raw, {
                "bytes": len(raw),
                "mtime_ns": after.st_mtime_ns,
                "sha256": hashlib.sha256(raw).hexdigest().upper(),
            }
        time.sleep(retry_seconds)
    raise RuntimeError(f"could not obtain a consistent gold snapshot: {path}")


def wait_for_quiet_snapshot(path, quiet_seconds=60.0, poll_seconds=2.0):
    """Return a snapshot whose identity stayed unchanged for the quiet window."""
    stable_since = time.monotonic()
    raw, identity = consistent_snapshot(path)
    print("gold candidate: " + json.dumps(identity, ensure_ascii=False), flush=True)
    while time.monotonic() - stable_since < quiet_seconds:
        time.sleep(poll_seconds)
        candidate_raw, candidate_identity = consistent_snapshot(path)
        if candidate_identity != identity:
            identity = candidate_identity
            raw = candidate_raw
            stable_since = time.monotonic()
            print(
                "gold changed; quiet timer reset: "
                + json.dumps(identity, ensure_ascii=False),
                flush=True,
            )
        else:
            raw = candidate_raw
            elapsed = time.monotonic() - stable_since
            print(
                f"gold quiet {elapsed:.1f}/{quiet_seconds:.1f}s "
                f"sha256={identity['sha256']}",
                flush=True,
            )
    return raw, identity


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--quiet-seconds", type=float, default=60.0)
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    args = parser.parse_args()
    _raw, identity = wait_for_quiet_snapshot(
        args.path, args.quiet_seconds, args.poll_seconds
    )
    print("STABLE_GOLD=" + json.dumps(identity, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
