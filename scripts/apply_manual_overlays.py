#!/usr/bin/env python3
"""Merge base district data with optional manual overlay files."""

from __future__ import annotations

import argparse
import copy
import json
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
BASE_DIR = DATA_DIR / "base"
OVERLAY_DIR = DATA_DIR / "overlays"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply manual overlay JSON files on top of base district data.",
    )
    parser.add_argument(
        "--district-code",
        help="Only build one district code. Defaults to all base district JSON files.",
    )
    parser.add_argument(
        "--base-dir",
        default=str(BASE_DIR),
        help="Directory containing base district JSON files.",
    )
    parser.add_argument(
        "--overlay-dir",
        default=str(OVERLAY_DIR),
        help="Directory containing manual overlay JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DATA_DIR),
        help="Directory to write merged district JSON files into.",
    )
    return parser.parse_args()


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)

    for key, value in patch.items():
        if value is None:
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)

    return merged


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_matches(candidate: dict[str, Any], matcher: dict[str, Any]) -> bool:
    for key, expected in matcher.items():
        if expected is None:
            continue
        if str(candidate.get(key)) != str(expected):
            return False
    return True


def is_meaningful_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def build_candidate_patch(entry: dict[str, Any]) -> dict[str, Any]:
    patch = copy.deepcopy(entry.get("patch", {}))
    field_sources = entry.get("fieldSources", {})
    field_notes = entry.get("fieldNotes", {})

    meaningful_fields = {
        key for key, value in patch.items() if key not in {"fieldSources", "fieldNotes"} and is_meaningful_value(value)
    }

    if isinstance(field_sources, dict):
        active_sources = {
            key: value for key, value in field_sources.items() if key in meaningful_fields and is_meaningful_value(value)
        }
        if active_sources:
            patch["fieldSources"] = deep_merge(patch.get("fieldSources", {}), active_sources)

    if isinstance(field_notes, dict):
        active_notes = {
            key: value for key, value in field_notes.items() if key in meaningful_fields and is_meaningful_value(value)
        }
        if active_notes:
            patch["fieldNotes"] = deep_merge(patch.get("fieldNotes", {}), active_notes)

    return patch


def merge_candidate_list(
    candidates: list[dict[str, Any]],
    overlay_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged_candidates = [copy.deepcopy(candidate) for candidate in candidates]

    for entry in overlay_candidates:
        matcher = entry.get("match", {})
        patch = build_candidate_patch(entry)
        if not matcher or not patch:
            continue

        target = next((candidate for candidate in merged_candidates if candidate_matches(candidate, matcher)), None)
        if target is None:
            continue

        target_index = merged_candidates.index(target)
        merged_candidates[target_index] = deep_merge(target, patch)

    return merged_candidates


def apply_overlay(base_payload: dict[str, Any], overlay_payload: dict[str, Any], overlay_path: Path) -> dict[str, Any]:
    merged = copy.deepcopy(base_payload)
    merged["election"] = deep_merge(merged.get("election", {}), overlay_payload.get("election", {}))
    merged["district"] = deep_merge(merged.get("district", {}), overlay_payload.get("district", {}))
    merged["candidates"] = merge_candidate_list(
        merged.get("candidates", []),
        overlay_payload.get("candidates", []),
    )

    existing_meta = merged.get("meta", {}) if isinstance(merged.get("meta"), dict) else {}
    overlay_meta = overlay_payload.get("meta", {}) if isinstance(overlay_payload.get("meta"), dict) else {}
    merged["meta"] = deep_merge(
        existing_meta,
        {
            "basePath": str(overlay_path.parent.parent / "base" / overlay_path.name).replace(str(ROOT) + "/", ""),
            "overlayPath": str(overlay_path).replace(str(ROOT) + "/", ""),
            "overlayApplied": True,
            "mergedAt": time.strftime("%Y-%m-%d %H:%M:%S KST", time.localtime()),
        },
    )
    merged["meta"] = deep_merge(merged["meta"], overlay_meta)

    return merged


def merge_one(base_path: Path, overlay_path: Path | None, output_path: Path) -> None:
    base_payload = load_json(base_path)
    merged = copy.deepcopy(base_payload)

    merged["meta"] = deep_merge(
        merged.get("meta", {}) if isinstance(merged.get("meta"), dict) else {},
        {
            "basePath": str(base_path).replace(str(ROOT) + "/", ""),
            "overlayApplied": False,
            "mergedAt": time.strftime("%Y-%m-%d %H:%M:%S KST", time.localtime()),
        },
    )

    if overlay_path and overlay_path.exists():
        overlay_payload = load_json(overlay_path)
        merged = apply_overlay(base_payload, overlay_payload, overlay_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    base_dir = Path(args.base_dir)
    overlay_dir = Path(args.overlay_dir)
    output_dir = Path(args.output_dir)

    if args.district_code:
        base_paths = [base_dir / f"district-{args.district_code}.json"]
    else:
        base_paths = sorted(base_dir.glob("district-*.json"))

    if not base_paths:
        raise SystemExit(f"No base district files found in {base_dir}")

    built = 0
    for base_path in base_paths:
        if not base_path.exists():
            raise SystemExit(f"Missing base file: {base_path}")

        code = base_path.stem.removeprefix("district-")
        overlay_path = overlay_dir / f"district-{code}.json"
        output_path = output_dir / f"district-{code}.json"
        merge_one(base_path, overlay_path if overlay_path.exists() else None, output_path)
        built += 1

    print(f"Wrote {built} merged district files to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
