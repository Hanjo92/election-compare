#!/usr/bin/env python3
"""Inspect NEC code information APIs such as election code lists."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
API_BASE = "https://apis.data.go.kr/9760000/CommonCodeService"
SG_CODE_ENDPOINT = f"{API_BASE}/getCommonSgCodeList"


def load_local_env(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[key] = value


def require_service_key() -> str:
    load_local_env(ROOT / ".env.local")
    service_key = os.getenv("NEC_API_KEY") or os.getenv("DATA_GO_KR_SERVICE_KEY")
    if not service_key:
        raise SystemExit("Missing service key. Set NEC_API_KEY or DATA_GO_KR_SERVICE_KEY.")
    return urllib.parse.unquote(service_key.strip())


def api_get(url: str, params: dict[str, Any]) -> dict[str, Any]:
    query = urllib.parse.urlencode({**params, "resultType": "json"}, doseq=True, safe=":/")
    request = urllib.request.Request(f"{url}?{query}", headers={"User-Agent": "BallotMirror/0.1"})

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise SystemExit(
                "HTTP 403 from NEC code API. "
                "Apply for 중앙선거관리위원회_코드 정보 (data.go.kr 15000897) first."
            ) from exc
        raise

    data = json.loads(payload)
    header = data.get("response", {}).get("header", {})
    result_code = str(header.get("resultCode", ""))
    if result_code not in {"00", "INFO-00"}:
        raise SystemExit(f"Code API error {result_code}: {header.get('resultMsg')}")
    return data


def extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    if isinstance(items, dict):
        return [items]
    return items


def fetch_election_codes(service_key: str, page_size: int) -> list[dict[str, Any]]:
    payload = api_get(
        SG_CODE_ENDPOINT,
        {
            "ServiceKey": service_key,
            "pageNo": 1,
            "numOfRows": page_size,
        },
    )
    return extract_items(payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect NEC code information API responses.")
    parser.add_argument(
        "--contains",
        help="Only show election codes whose sgName contains this text.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of election code rows to request.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    service_key = require_service_key()
    rows = fetch_election_codes(service_key, args.limit)

    if args.contains:
        rows = [row for row in rows if args.contains in str(row.get("sgName", ""))]

    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
