#!/usr/bin/env python3
"""Build merged data, district pages, and homepage index in one command."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_step(*args: str) -> None:
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def main() -> int:
    run_step("scripts/apply_manual_overlays.py")
    run_step("scripts/sync_district_pages.py")
    run_step("scripts/build_district_index.py")
    print("Site build complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
