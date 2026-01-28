import csv
import io
import re
import sys
from typing import Dict, List, Any

import requests
import yaml

def norm(s: str) -> str:
    return (s or "").strip()

def to_int_year(s: str) -> int:
    digits = re.sub(r"[^0-9]", "", norm(s))
    return int(digits) if digits else 0

def clean_item(row: Dict[str, str]) -> Dict[str, Any]:
    item = {
        "year": to_int_year(row.get("year", "")),
        "title": norm(row.get("title", "")),
        "authors": norm(row.get("authors", "")),
        "venue": norm(row.get("venue", "")),
        "link": norm(row.get("link", "")),
    }
    # 빈 값 제거
    return {k: v for k, v in item.items() if v not in ["", 0]}

def main(csv_url: str, out_journal: str, out_conf_int: str, out_conf_dom: str):
    r = requests.get(csv_url, timeout=30)
    r.raise_for_status()

    reader = csv.DictReader(io.StringIO(r.text))

    buckets: Dict[str, List[Dict[str, Any]]] = {
        "journal": [],
        "conf_international": [],
        "conf_domestic": [],
    }

    for row in reader:
        t = norm(row.get("type", "")).lower()
        year = to_int_year(row.get("year", ""))
        title = norm(row.get("title", ""))

        if not year or not title:
            continue

        if t not in buckets:
            # type 오타/누락이면 스킵(원하면 journal로 보내도록 바꿀 수도 있음)
            continue

        buckets[t].append(clean_item(row))

    # 최신이 위로 오게 정렬
    for k in buckets:
        buckets[k].sort(key=lambda x: (x.get("year", 0), x.get("title", "")), reverse=True)

    with open(out_journal, "w", encoding="utf-8") as f:
        yaml.safe_dump(buckets["journal"], f, allow_unicode=True, sort_keys=False)
    with open(out_conf_int, "w", encoding="utf-8") as f:
        yaml.safe_dump(buckets["conf_international"], f, allow_unicode=True, sort_keys=False)
    with open(out_conf_dom, "w", encoding="utf-8") as f:
        yaml.safe_dump(buckets["conf_domestic"], f, allow_unicode=True, sort_keys=False)

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python scripts/sync_pubs_split.py <csv_url> <out_journal> <out_conf_int> <out_conf_dom>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
