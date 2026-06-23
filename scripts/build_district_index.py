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
    election_map = {}

    for path in sorted((DATA_DIR / "elections").glob("*/district-*.json")):

        payload = json.loads(path.read_text(encoding="utf-8"))
        district = payload.get("district", {})
        election = payload.get("election", {})
        candidates = payload.get("candidates", [])
        code = district.get("code") or path.stem.removeprefix("district-")
        election_id = election.get("id", "unknown")
        election_type = str(election.get("type", "")).strip()
        election_key = f"{election_id}:{election_type}" if election_type else str(election_id)
        election_name = election.get("name", "선거 정보")
        candidate_count = len(candidates)

        district_row = {
            "code": code,
            "name": district.get("name", code),
            "region": district.get("region", "전국"),
            "electionId": election_id,
            "electionTypecode": election_type,
            "electionKey": election_key,
            "electionName": election_name,
            "candidateCount": candidate_count,
            "path": f"./district/?electionId={election_id}&code={code}",
            "legacyPath": f"./district/{election_id}/{code}/",
        }
        districts.append(district_row)

        if election_key not in election_map:
            election_map[election_key] = {
                "key": election_key,
                "id": election_id,
                "type": election_type,
                "name": election_name,
                "districtCount": 0,
                "candidateCount": 0,
            }

        election_map[election_key]["districtCount"] += 1
        election_map[election_key]["candidateCount"] += candidate_count

    elections = sorted(
        election_map.values(),
        key=lambda election: (str(election["id"]), str(election.get("type", ""))),
        reverse=True,
    )

    output = {
        "updatedAt": time.strftime("%Y-%m-%d %H:%M:%S KST", time.localtime()),
        "elections": elections,
        "districts": districts,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(districts)} districts to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
