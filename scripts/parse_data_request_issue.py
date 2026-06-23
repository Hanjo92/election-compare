#!/usr/bin/env python3
"""Parse a GitHub issue body for district data requests."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


FIELD_MAP = {
    "electionid": "sgId",
    "electiontypecode": "sgTypecode",
    "electionname": "electionName",
    "region": "sdName",
    "districtname": "sggName",
    "districtcode": "districtCode",
}
REQUIRED_FIELDS = ("sgId", "sgTypecode", "sdName", "sggName", "districtCode")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse district data request issue body.")
    parser.add_argument("--body-file", required=True, help="Path to the issue body markdown file.")
    parser.add_argument(
        "--output",
        required=True,
        help="Where to write the normalized JSON request payload.",
    )
    return parser.parse_args()


def normalize_key(raw: str) -> str:
    return re.sub(r"[^a-z0-9]", "", raw.lower())


def parse_body(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("- ") or ":" not in line:
            continue

        key, value = line[2:].split(":", 1)
        mapped_key = FIELD_MAP.get(normalize_key(key))
        if not mapped_key:
            continue

        cleaned_value = value.strip()
        if cleaned_value:
            parsed[mapped_key] = cleaned_value

    missing = [field for field in REQUIRED_FIELDS if not parsed.get(field)]
    if missing:
        raise SystemExit(f"Missing required request fields: {', '.join(missing)}")

    return parsed


def main() -> int:
    args = parse_args()
    body_path = Path(args.body_file)
    payload = parse_body(body_path.read_text(encoding="utf-8"))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote parsed request to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
