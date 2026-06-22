#!/usr/bin/env python3
"""Build a homepage district index from district JSON files."""

from __future__ import annotations

import json
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT = DATA_DIR / "district-index.json"


def main() -> int:
    districts = []

    for path in sorted(DATA_DIR.glob("district-*.json")):
        if path.name == OUTPUT.name:
            continue

        payload = json.loads(path.read_text(encoding="utf-8"))
        district = payload.get("district", {})
        election = payload.get("election", {})
        candidates = payload.get("candidates", [])
        code = district.get("code") or path.stem.removeprefix("district-")

        districts.append(
            {
                "code": code,
                "name": district.get("name", code),
                "region": district.get("region", "전국"),
                "electionName": election.get("name", "선거 정보"),
                "candidateCount": len(candidates),
                "path": f"./district/{code}/",
            },
        )

    output = {
        "updatedAt": time.strftime("%Y-%m-%d %H:%M:%S KST", time.localtime()),
        "districts": districts,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(districts)} districts to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
