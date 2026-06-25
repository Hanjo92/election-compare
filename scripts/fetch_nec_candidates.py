#!/usr/bin/env python3
"""Fetch candidate data from NEC open APIs and emit district JSON for the prototype."""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


API_BASE = "https://apis.data.go.kr/9760000"
PROFILE_ENDPOINT = f"{API_BASE}/PofelcddInfoInqireService/getPofelcddRegistSttusInfoInqire"
PLEDGE_ENDPOINT = f"{API_BASE}/ElecPrmsInfoInqireService/getCnddtElecPrmsInfoInqire"
PLEDGE_SUPPORTED_TYPES = {"1", "3", "4", "11"}
ROOT = Path(__file__).resolve().parents[1]


@dataclass
class FetchContext:
    service_key: str
    sg_id: str
    sg_typecode: str
    sd_name: str | None
    sgg_name: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch NEC candidate data and build a district JSON file for Ballot Mirror.",
    )
    parser.add_argument("--service-key", help="data.go.kr service key. Defaults to NEC_API_KEY env var.")
    parser.add_argument("--sg-id", required=True, help="Election ID, e.g. 20240410")
    parser.add_argument("--sg-typecode", required=True, help="Election type code, e.g. 2 or 4")
    parser.add_argument("--sd-name", help="Province/metro name, e.g. 서울특별시")
    parser.add_argument("--sgg-name", help="District name, e.g. 종로구 or 서초구갑")
    parser.add_argument(
        "--district-code",
        required=True,
        help="ASCII code used by the site route, e.g. seocho-gu-gap",
    )
    parser.add_argument(
        "--election-name",
        default=None,
        help="Optional display name to override API-derived election label.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path. Defaults to data/base/<sg-id>/district-<district-code>.json",
    )
    return parser.parse_args()


def require_service_key(explicit_key: str | None) -> str:
    load_local_env(ROOT / ".env.local")
    service_key = explicit_key or os.getenv("NEC_API_KEY") or os.getenv("DATA_GO_KR_SERVICE_KEY")
    if service_key:
        return urllib.parse.unquote(service_key.strip())

    raise SystemExit(
        "Missing service key. Pass --service-key or set NEC_API_KEY / DATA_GO_KR_SERVICE_KEY.",
    )


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


def api_get(url: str, params: dict[str, Any]) -> dict[str, Any]:
    query = urllib.parse.urlencode({**params, "resultType": "json"}, doseq=True, safe=":/")
    request = urllib.request.Request(f"{url}?{query}", headers={"User-Agent": "BallotMirror/0.1"})

    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read().decode("utf-8")

    data = json.loads(payload)
    response_body = data.get("response", {})
    header = response_body.get("header", {})
    result_code = str(header.get("resultCode", ""))

    if result_code == "INFO-03":
        raise RuntimeError(
            "API returned INFO-03 (no data). "
            "This usually means the sgId/sgTypecode/district parameters do not match data currently exposed by this service.",
        )

    if result_code not in {"00", "INFO-00"}:
        raise RuntimeError(f"API error {result_code}: {header.get('resultMsg')}")

    return data


def extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    body = payload.get("response", {}).get("body", {})
    items = body.get("items", {}).get("item", [])
    if isinstance(items, dict):
        return [items]
    return items


def fetch_all(url: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    page_no = 1
    rows = 100
    all_items: list[dict[str, Any]] = []

    while True:
        payload = api_get(url, {**params, "pageNo": page_no, "numOfRows": rows})
        body = payload.get("response", {}).get("body", {})
        items = extract_items(payload)
        all_items.extend(items)

        total_count = int(body.get("totalCount", len(all_items) or 0))
        if len(all_items) >= total_count or not items:
            return all_items

        page_no += 1
        time.sleep(0.15)


def first_nonempty(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text != "-":
            return text
    return None


def fetch_pledges(context: FetchContext, candidate_id: str) -> list[dict[str, str]]:
    if context.sg_typecode not in PLEDGE_SUPPORTED_TYPES:
        return []

    try:
        items = fetch_all(
            PLEDGE_ENDPOINT,
            {
                "ServiceKey": context.service_key,
                "sgId": context.sg_id,
                "sgTypecode": context.sg_typecode,
                "cnddtId": candidate_id,
            },
        )
    except RuntimeError as exc:
        if "INFO-03" in str(exc):
            return []
        raise

    pledges: list[dict[str, str]] = []
    for item in items:
        title = first_nonempty(item.get("prmsTitle"), item.get("prmsRealmName"), item.get("title"))
        summary = first_nonempty(
            item.get("prmsCont"),
            item.get("prmsTitle"),
            item.get("prmsCn"),
            "자료 미확인",
        )
        if not title:
            title = "공약"
        pledges.append(
            {
                "title": title,
                "summary": summary,
                "source": "https://www.data.go.kr/data/15040587/openapi.do",
            },
        )

    return pledges[:5]


def normalize_candidate(context: FetchContext, item: dict[str, Any]) -> dict[str, Any]:
    candidate_id = str(first_nonempty(item.get("huboid"), item.get("cnddtId"), item.get("candidateId")) or "")
    career_parts = [first_nonempty(item.get("career1")), first_nonempty(item.get("career2"))]
    careers = [entry for entry in career_parts if entry]

    return {
        "id": candidate_id or first_nonempty(item.get("name"), item.get("num")) or "candidate",
        "name": first_nonempty(item.get("name"), "이름 미확인"),
        "party": first_nonempty(item.get("jdName"), "정당 미확인"),
        "number": first_nonempty(item.get("num"), "-"),
        "incumbent": False,
        "incumbentLabel": "자료 미확인",
        "age": first_nonempty(item.get("age"), "자료 미확인"),
        "job": first_nonempty(item.get("job"), "자료 미확인"),
        "education": first_nonempty(item.get("edu"), "자료 미확인"),
        "career": careers or ["자료 미확인"],
        "assets": "자료 미확인",
        "military": "자료 미확인",
        "tax": "자료 미확인",
        "crime": "자료 미확인",
        "pledges": fetch_pledges(context, candidate_id) if candidate_id else [],
        "sources": {
            "profile": "https://www.data.go.kr/data/15000908/openapi.do",
            "policy": "https://www.data.go.kr/data/15040587/openapi.do",
            "data": "https://data.nec.go.kr/",
        },
    }


def build_payload(args: argparse.Namespace, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S KST", time.localtime())
    return {
        "election": {
            "id": args.sg_id,
            "name": args.election_name or f"선거 {args.sg_id} / 종류코드 {args.sg_typecode}",
            "type": args.sg_typecode,
            "updatedAt": timestamp,
        },
        "district": {
            "code": args.district_code,
            "name": args.sgg_name or args.sd_name or args.district_code,
            "region": args.sd_name or "전국",
        },
        "candidates": candidates,
    }


def load_existing_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def payload_for_comparison(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(payload)
    election = normalized.get("election")
    if isinstance(election, dict):
        election.pop("updatedAt", None)
    return normalized


def main() -> int:
    args = parse_args()
    service_key = require_service_key(args.service_key)

    context = FetchContext(
        service_key=service_key,
        sg_id=args.sg_id,
        sg_typecode=args.sg_typecode,
        sd_name=args.sd_name,
        sgg_name=args.sgg_name,
    )

    query = {
        "ServiceKey": service_key,
        "sgId": args.sg_id,
        "sgTypecode": args.sg_typecode,
    }
    if args.sd_name:
        query["sdName"] = args.sd_name
    if args.sgg_name:
        query["sggName"] = args.sgg_name

    raw_candidates = fetch_all(PROFILE_ENDPOINT, query)
    normalized = [normalize_candidate(context, item) for item in raw_candidates]
    normalized.sort(key=lambda candidate: str(candidate["number"]))

    output_path = Path(args.output or f"data/base/{args.sg_id}/district-{args.district_code}.json")
    existing_payload = load_existing_payload(output_path)
    payload = build_payload(args, normalized)

    if existing_payload and payload_for_comparison(existing_payload) == payload_for_comparison(payload):
        payload["election"]["updatedAt"] = existing_payload.get("election", {}).get(
            "updatedAt",
            payload["election"]["updatedAt"],
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {len(normalized)} candidates to {output_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
