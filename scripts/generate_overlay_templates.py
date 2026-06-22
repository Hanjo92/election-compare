#!/usr/bin/env python3
"""Generate editable overlay template files from base district JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
BASE_DIR = DATA_DIR / "base"
OVERLAY_DIR = DATA_DIR / "overlays"
DEFAULT_FIELDS = ["assets", "military", "tax", "crime", "incumbentLabel"]
DEFAULT_SOURCE = {
    "label": "후보자공보",
    "url": "https://info.nec.go.kr/",
}
DEFAULT_NOTES = {
    "assets": "재산신고액 기준",
    "military": "병역사항 요약",
    "tax": "최근 체납사실 기준",
    "crime": "전과기록 기준",
    "incumbentLabel": "현직 기재 기준",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate manual overlay template files for one or more districts.",
    )
    parser.add_argument(
        "--district-code",
        help="Only generate one district code. Defaults to all base district JSON files.",
    )
    parser.add_argument(
        "--config",
        help="Optional batch config JSON path. When set, generate overlays for those district codes.",
    )
    parser.add_argument(
        "--base-dir",
        default=str(BASE_DIR),
        help="Directory containing base district JSON files.",
    )
    parser.add_argument(
        "--overlay-dir",
        default=str(OVERLAY_DIR),
        help="Directory to write overlay template files into.",
    )
    parser.add_argument(
        "--fields",
        default=",".join(DEFAULT_FIELDS),
        help="Comma-separated candidate fields to include in the template.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing overlay files.",
    )
    parser.add_argument(
        "--allow-missing-base",
        action="store_true",
        help="When used with --config, create empty overlay stubs for districts whose base JSON does not exist yet.",
    )
    return parser.parse_args()


def build_candidate_template(candidate: dict, fields: list[str]) -> dict:
    patch = {field: None for field in fields}
    field_sources = {field: DEFAULT_SOURCE for field in fields}
    field_notes = {field: DEFAULT_NOTES.get(field, "출처 메모 작성") for field in fields}

    return {
        "match": {
            "id": candidate.get("id"),
            "name": candidate.get("name"),
            "number": candidate.get("number"),
        },
        "patch": patch,
        "fieldSources": field_sources,
        "fieldNotes": field_notes,
    }


def build_overlay_template(payload: dict, fields: list[str]) -> dict:
    district = payload.get("district", {})
    return {
        "meta": {
            "updatedAt": "",
            "note": f"{district.get('name', district.get('code', '지역구'))} 수동 보강 템플릿",
            "template": True,
            "instructions": [
                "patch 값이 null이면 병합 시 무시됩니다.",
                "채운 필드만 merged JSON에 반영됩니다.",
                "fieldSources와 fieldNotes는 후보자공보 기준 기본값입니다.",
            ],
        },
        "candidates": [
            build_candidate_template(candidate, fields) for candidate in payload.get("candidates", [])
        ],
    }


def load_config_districts(config_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    regions = payload.get("regions", [])
    districts: list[dict[str, Any]] = []

    if isinstance(regions, list):
        for region in regions:
            if not isinstance(region, dict) or region.get("enabled") is False:
                continue
            sd_name = region.get("sdName")
            for district in region.get("districts", []):
                if not isinstance(district, dict) or district.get("enabled") is False:
                    continue
                districts.append(
                    {
                        "districtCode": district.get("districtCode"),
                        "sggName": district.get("sggName"),
                        "sdName": district.get("sdName") or sd_name,
                    }
                )

    flat_districts = payload.get("districts", [])
    if isinstance(flat_districts, list):
        for district in flat_districts:
            if not isinstance(district, dict) or district.get("enabled") is False:
                continue
            districts.append(
                {
                    "districtCode": district.get("districtCode"),
                    "sggName": district.get("sggName"),
                    "sdName": district.get("sdName") or payload.get("sdName"),
                }
            )

    return [district for district in districts if district.get("districtCode")]


def build_empty_overlay_template(district: dict[str, Any]) -> dict:
    district_name = district.get("sggName") or district.get("districtCode") or "지역구"
    return {
        "meta": {
            "updatedAt": "",
            "note": f"{district_name} 수동 보강 템플릿",
            "template": True,
            "placeholder": True,
            "instructions": [
                "base JSON이 아직 없어 후보 match 목록은 비어 있습니다.",
                "실데이터 수집 후 --force로 템플릿을 다시 생성하면 후보별 match가 채워집니다.",
                "필요하면 district 메타와 notes를 먼저 적어둘 수 있습니다.",
            ],
        },
        "district": {
            "code": district.get("districtCode"),
            "name": district.get("sggName"),
            "region": district.get("sdName"),
        },
        "candidates": [],
    }


def detect_election_id(payload: dict[str, Any], fallback: str | None = None) -> str:
    election = payload.get("election", {})
    election_id = str(election.get("id") or fallback or "").strip()
    if not election_id:
        raise SystemExit("Could not determine election id for overlay template generation.")
    return election_id


def main() -> int:
    args = parse_args()
    base_dir = Path(args.base_dir)
    overlay_dir = Path(args.overlay_dir)
    fields = [field.strip() for field in args.fields.split(",") if field.strip()]

    overlay_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    skipped = 0

    if args.config:
        config_path = Path(args.config)
        districts = load_config_districts(config_path)
        config_payload = json.loads(config_path.read_text(encoding="utf-8"))
        election_id = str(config_payload.get("sgId") or "").strip()
        if not districts:
            raise SystemExit(f"No enabled districts found in config: {config_path}")

        for district in districts:
            code = district["districtCode"]
            base_path = base_dir / election_id / f"district-{code}.json"
            output_path = overlay_dir / election_id / f"district-{code}.json"
            if output_path.exists() and not args.force:
                skipped += 1
                continue

            if base_path.exists():
                payload = json.loads(base_path.read_text(encoding="utf-8"))
                template = build_overlay_template(payload, fields)
            elif args.allow_missing_base:
                template = build_empty_overlay_template(district)
            else:
                raise SystemExit(f"Missing base file: {base_path}")

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            written += 1
    else:
        if args.district_code:
            base_paths = sorted(base_dir.glob(f"*/district-{args.district_code}.json"))
        else:
            base_paths = sorted(base_dir.glob("*/district-*.json"))

        if not base_paths:
            raise SystemExit(f"No base district files found in {base_dir}")

        for base_path in base_paths:
            if not base_path.exists():
                raise SystemExit(f"Missing base file: {base_path}")

            code = base_path.stem.removeprefix("district-")
            payload = json.loads(base_path.read_text(encoding="utf-8"))
            election_id = detect_election_id(payload, base_path.parent.name)
            output_path = overlay_dir / election_id / f"district-{code}.json"
            if output_path.exists() and not args.force:
                skipped += 1
                continue

            template = build_overlay_template(payload, fields)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            written += 1

    print(f"Wrote {written} overlay templates to {overlay_dir} (skipped {skipped})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
