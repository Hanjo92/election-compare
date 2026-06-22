#!/usr/bin/env python3
"""Fetch multiple districts from NEC APIs using a single batch config file."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "election-batch.sample.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch multiple district JSON files from NEC APIs using one config file.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help="Batch config JSON path.",
    )
    parser.add_argument(
        "--build-site",
        action="store_true",
        help="Run build_site.py after all district fetches finish.",
    )
    parser.add_argument(
        "--generate-overlays",
        action="store_true",
        help="Run generate_overlay_templates.py after fetches.",
    )
    parser.add_argument(
        "--force-overlays",
        action="store_true",
        help="Used with --generate-overlays to overwrite existing overlay files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned fetch commands without executing them.",
    )
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing batch config: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in batch config {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise SystemExit("Batch config must be a JSON object.")
    return payload


def require_text(config: dict[str, Any], key: str) -> str:
    value = str(config.get(key, "")).strip()
    if not value:
        raise SystemExit(f"Batch config is missing required field: {key}")
    return value


def build_common_config(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "sgId": config.get("sgId"),
        "sgTypecode": config.get("sgTypecode"),
        "sdName": config.get("sdName"),
        "electionName": config.get("electionName"),
        "serviceKey": config.get("serviceKey"),
    }


def merge_dicts(*configs: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for config in configs:
        for key, value in config.items():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            merged[key] = value
    return merged


def normalize_district_entry(district: dict[str, Any], inherited: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(district, dict):
        raise SystemExit("Each district entry must be a JSON object.")
    if district.get("enabled") is False:
        return {}

    normalized = merge_dicts(inherited, district)
    if "districtCode" not in normalized:
        raise SystemExit("Each district entry must include districtCode.")
    return normalized


def collect_districts(config: dict[str, Any]) -> list[dict[str, Any]]:
    common = build_common_config(config)
    districts: list[dict[str, Any]] = []

    flat_districts = config.get("districts", [])
    if flat_districts:
        if not isinstance(flat_districts, list):
            raise SystemExit("'districts' must be a list when provided.")
        for district in flat_districts:
            normalized = normalize_district_entry(district, common)
            if normalized:
                districts.append(normalized)

    region_groups = config.get("regions", [])
    if region_groups:
        if not isinstance(region_groups, list):
            raise SystemExit("'regions' must be a list when provided.")
        for region in region_groups:
            if not isinstance(region, dict):
                raise SystemExit("Each region entry must be a JSON object.")
            if region.get("enabled") is False:
                continue
            region_common = merge_dicts(common, region)
            region_districts = region.get("districts", [])
            if not isinstance(region_districts, list) or not region_districts:
                raise SystemExit("Each region entry must include a non-empty districts list.")
            for district in region_districts:
                normalized = normalize_district_entry(district, region_common)
                if normalized:
                    districts.append(normalized)

    if not districts:
        raise SystemExit("Batch config must include at least one enabled district in 'districts' or 'regions'.")

    return districts


def build_fetch_command(common: dict[str, Any], district: dict[str, Any]) -> list[str]:
    district_code = require_text(district, "districtCode")
    sg_id = require_text(merge_dicts(common, district), "sgId")
    sg_typecode = require_text(merge_dicts(common, district), "sgTypecode")

    cmd = [
        sys.executable,
        "scripts/fetch_nec_candidates.py",
        "--sg-id",
        sg_id,
        "--sg-typecode",
        sg_typecode,
        "--district-code",
        district_code,
    ]

    sgg_name = str(district.get("sggName") or "").strip()
    if sgg_name:
        cmd.extend(["--sgg-name", sgg_name])

    sd_name = str(district.get("sdName") or common.get("sdName") or "").strip()
    if sd_name:
        cmd.extend(["--sd-name", sd_name])

    election_name = str(district.get("electionName") or common.get("electionName") or "").strip()
    if election_name:
        cmd.extend(["--election-name", election_name])

    output = str(district.get("output") or "").strip()
    if output:
        cmd.extend(["--output", output])

    service_key = str(district.get("serviceKey") or common.get("serviceKey") or "").strip()
    if service_key:
        cmd.extend(["--service-key", service_key])

    return cmd


def run_command(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=ROOT, check=True)


def print_command(cmd: list[str]) -> None:
    pretty = " ".join(f'"{part}"' if " " in part else part for part in cmd)
    print(pretty)


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    config = load_config(config_path)
    common = build_common_config(config)
    districts = collect_districts(config)
    commands = [build_fetch_command(common, district) for district in districts]

    if args.dry_run:
        print(f"Planned {len(commands)} fetch commands from {config_path}:")
        for cmd in commands:
            print_command(cmd)
        return 0

    for index, cmd in enumerate(commands, start=1):
        print(f"[{index}/{len(commands)}] Fetching district...")
        run_command(cmd)

    if args.generate_overlays:
        overlay_cmd = [sys.executable, "scripts/generate_overlay_templates.py"]
        if args.force_overlays:
            overlay_cmd.append("--force")
        run_command(overlay_cmd)

    if args.build_site:
        run_command([sys.executable, "scripts/build_site.py"])

    print(f"Batch fetch complete for {len(commands)} districts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
