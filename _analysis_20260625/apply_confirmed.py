# -*- coding: utf-8 -*-
"""Compatibility entry point for the canonical confirmed-tier applicator.

Keep the historical command name working without maintaining a second copy of
the pipeline.  In particular, newer confirmed-entry fields such as
``boundary_only`` are consumed by :mod:`apply_confirmed_now` in exactly one
place.
"""
from pathlib import Path
import runpy


runpy.run_path(str(Path(__file__).with_name("apply_confirmed_now.py")), run_name="__main__")
