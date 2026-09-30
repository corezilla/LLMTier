"""Repo-root pytest bootstrap.

Determinism guard for stale bytecode.

CPython's default (timestamp) bytecode invalidation keys on the source file's
mtime **and size**. When the working tree is populated by a tool that preserves
mtimes (rsync from a snapshot), a `.pyc` compiled from an earlier revision can
survive if that revision had the *same* source mtime and byte length — e.g. a
ternary whose two string constants were swapped (`"error" if x else "upstream"`
vs `"upstream" if x else "error"` has identical size). The stale `.pyc` is then
imported silently and an unrelated assertion fails nondeterministically.

Purging the local `__pycache__` trees once per session removes that entire class
of nondeterminism at negligible cost (a few hundred files). Set
``LLMTIER_KEEP_PYCACHE=1`` to opt out (e.g. when measuring import speed).
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

_ROOT = Path(__file__).resolve().parent


def _purge_bytecode() -> None:
    if os.environ.get("LLMTIER_KEEP_PYCACHE"):
        return
    for base in (_ROOT / "src", _ROOT / "tests"):
        if not base.is_dir():
            continue
        for cache_dir in base.rglob("__pycache__"):
            shutil.rmtree(cache_dir, ignore_errors=True)


_purge_bytecode()
