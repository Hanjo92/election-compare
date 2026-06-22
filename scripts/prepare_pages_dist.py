#!/usr/bin/env python3
"""Prepare a clean dist directory for GitHub Pages deployment."""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
INCLUDE_FILES = ["index.html", "about.html"]
INCLUDE_DIRS = ["assets", "district", "data"]


def reset_dist() -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)


def copy_site_files() -> None:
    for filename in INCLUDE_FILES:
        source = ROOT / filename
        if source.exists():
            shutil.copy2(source, DIST_DIR / filename)

    for dirname in INCLUDE_DIRS:
        source = ROOT / dirname
        if source.exists():
            shutil.copytree(source, DIST_DIR / dirname)


def write_nojekyll() -> None:
    (DIST_DIR / ".nojekyll").write_text("", encoding="utf-8")


def main() -> int:
    reset_dist()
    copy_site_files()
    write_nojekyll()
    print(f"Prepared GitHub Pages dist at {DIST_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
