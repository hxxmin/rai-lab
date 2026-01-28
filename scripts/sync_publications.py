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

def journal_item(row: Dict[str, str]) -> Dict[str, Any]:
    item = {
        "year": to_int_year(row.get("year")),
        "title": norm(row.get("title")),
        "authors": norm(row.get("authors")),
        "journal": norm(row.get("journal")),
        "volume": norm(row.get("volume")),
        "number": norm(row.get("number")),
        "pages": norm(row.get("pages")),
        "link": norm(row.get("link")),
    }
    return {k: v for k, v in item.items() if v not in ["", 0]}

def conf_item(row: Dict[str, str]) -> Dict[str, Any]:
    item = {
        "year": to_int_year(row.get("year")),
        "title": norm(row.get("title")),
        "authors": norm(row.get("authors")),
        "conf": norm(row.get("conference")),
        "location": norm(row.get("location")),
        "month": norm(row.get("month")),
        "link": norm(row.get("link")),
    }
    return {k: v for k, v in item.items() if v not in ["", 0]}

def normalize_row(row: Dict[str, str]) -> Dict[str, str]:
    # 헤더에 공백 / BOM(﻿) / 대소문자 섞임 대응
    fixed = {}
    for k, v in row.items():
        if k is None:
            continue
        kk = k.strip().lower().lstrip("\ufeff")  # BOM 제거
        fixed[kk] = v
    return fixed

def main(csv_url, out_journal, out_conf_int, out_conf_dom):
    r = requests.get(csv_url, timeout=30)
    r.raise_for_status()

    reader = csv.DictReader(io.StringIO(r.text))

    journal, conf_int, conf_dom = [], [], []

    for row in reader:
        row = normalize_row(row)

        t = norm(row.get("type", "")).lower()
        year = to_int_year(row.get("year", ""))
        title = norm(row.get("title", ""))

        if not year or not title:
            continue

        if t == "journal":
            journal.append(journal_item(row))
        elif t == "conf_international":
            conf_int.append(conf_item(row))
        elif t == "conf_domestic":
            conf_dom.append(conf_item(row))

    for lst in (journal, conf_int, conf_dom):
        lst.sort(key=lambda x: (x["year"], x["title"]), reverse=True)

    with open(out_journal, "w", encoding="utf-8") as f:
        yaml.safe_dump(journal, f, allow_unicode=True, sort_keys=False)
    with open(out_conf_int, "w", encoding="utf-8") as f:
        yaml.safe_dump(conf_int, f, allow_unicode=True, sort_keys=False)
    with open(out_conf_dom, "w", encoding="utf-8") as f:
        yaml.safe_dump(conf_dom, f, allow_unicode=True, sort_keys=False)

if __name__ == "__main__":
    main(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
        sys.argv[4],
    )
