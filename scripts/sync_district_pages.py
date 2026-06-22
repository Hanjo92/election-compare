#!/usr/bin/env python3
"""Generate static district route pages from a shared HTML template."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
BASE_DIR = DATA_DIR / "base"
DISTRICT_DIR = ROOT / "district"
TEMPLATE_PATH = ROOT / "templates" / "district-page.html"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate district/<code>/index.html pages from template and base district JSON files.",
    )
    parser.add_argument(
        "--district-code",
        help="Only generate one district code. Defaults to all base district JSON files.",
    )
    parser.add_argument(
        "--base-dir",
        default=str(BASE_DIR),
        help="Directory containing base district JSON files.",
    )
    parser.add_argument(
        "--district-dir",
        default=str(DISTRICT_DIR),
        help="Directory containing generated district route folders.",
    )
    parser.add_argument(
        "--template",
        default=str(TEMPLATE_PATH),
        help="HTML template path used for each district page.",
    )
    return parser.parse_args()


def load_payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_title(payload: dict, fallback_code: str) -> str:
    district = payload.get("district", {})
    election = payload.get("election", {})
    district_name = district.get("name") or fallback_code
    election_name = election.get("name")
    if election_name:
        return f"{district_name} | {election_name}"
    return district_name


def main() -> int:
    args = parse_args()
    base_dir = Path(args.base_dir)
    district_dir = Path(args.district_dir)
    template_path = Path(args.template)

    if args.district_code:
        base_paths = [base_dir / f"district-{args.district_code}.json"]
    else:
        base_paths = sorted(base_dir.glob("district-*.json"))

    if not base_paths:
        raise SystemExit(f"No base district files found in {base_dir}")
    if not template_path.exists():
        raise SystemExit(f"Missing template: {template_path}")

    template = template_path.read_text(encoding="utf-8")
    written = 0

    for base_path in base_paths:
        if not base_path.exists():
            raise SystemExit(f"Missing base file: {base_path}")

        code = base_path.stem.removeprefix("district-")
        payload = load_payload(base_path)
        title = build_title(payload, code)
        page_html = template.replace("__DISTRICT_TITLE__", title)

        output_dir = district_dir / code
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "index.html"
        output_path.write_text(page_html, encoding="utf-8")
        written += 1

    print(f"Wrote {written} district pages to {district_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
