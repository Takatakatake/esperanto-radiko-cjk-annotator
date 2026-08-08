# -*- coding: utf-8 -*-
"""Deprecated compatibility entry point for the formal Kanji generator.

Keep exactly one implementation of KANJI_DECOMPOSE and reviewed overrides;
older copies here previously diverged from ``apply_kanji_now.py``.
"""
from pathlib import Path
import runpy


if __name__ == "__main__":
    print("[deprecated wrapper] forwarding to apply_kanji_now.py", flush=True)
    runpy.run_path(
        str(Path(__file__).with_name("apply_kanji_now.py")),
        run_name="__main__",
    )
