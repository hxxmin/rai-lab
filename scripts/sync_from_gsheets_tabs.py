import csv
import io
import re
import sys
from typing import Dict, List, Any, Optional

import requests
import yaml


# ---------- utils ----------
def norm(s: Optional[str]) -> str:
    return (s or "").strip()

def to_int_year(s: Optional[str]) -> int:
    digits = re.sub(r"[^0-9]", "", norm(s))
    return int(digits) if digits else 0

def normalize_row(row: Dict[str, str]) -> Dict[str, str]:
    """Handle BOM/space/case issues in CSV headers."""
    fixed = {}
    for k, v in row.items():
        if k is None:
            continue
        kk = k.strip().lower().lstrip("\ufeff")
        fixed[kk] = v
    return fixed

def fetch_csv_rows(csv_url: str) -> List[Dict[str, str]]:
    r = requests.get(csv_url, timeout=30)
    r.raise_for_status()
    # ✅ important: force UTF-8 (prevents Korean garbling)
    r.encoding = "utf-8"

    reader = csv.DictReader(io.StringIO(r.text))
    rows = []
    for row in reader:
        rows.append(normalize_row(row))
    return rows

def dump_yaml(items: List[Dict[str, Any]], out_path: str):
    # newest first by year/title if year exists
    if items and "year" in items[0]:
        items.sort(key=lambda x: (x.get("year", 0), x.get("title", "")), reverse=True)

    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(items, f, allow_unicode=True, sort_keys=False)


# ---------- mappings ----------
def journal_item(row: Dict[str, str]) -> Optional[Dict[str, Any]]:
    year = to_int_year(row.get("year"))
    title = norm(row.get("title"))
    if not year or not title:
        return None

    item: Dict[str, Any] = {
        "year": year,
        "title": title,
        "authors": norm(row.get("authors")),
        "journal": norm(row.get("journal")),
        "volume": norm(row.get("volume")),
        "number": norm(row.get("number")),
        "pages": norm(row.get("pages")),
        "link": norm(row.get("link")),
        "image_url": norm(row.get("image_url")),
    }
    # remove empty fields
    return {k: v for k, v in item.items() if v not in ["", 0]}

def conf_item(row: Dict[str, str]) -> Optional[Dict[str, Any]]:
    year = to_int_year(row.get("year"))
    title = norm(row.get("title"))
    if not year or not title:
        return None

    item: Dict[str, Any] = {
        "year": year,
        "title": title,
        "authors": norm(row.get("authors")),
        "conf": norm(row.get("conference")),
        "location": norm(row.get("location")),
        "month": norm(row.get("month")),
        "link": norm(row.get("link")),
        "image_url": norm(row.get("image_url")),
    }
    return {k: v for k, v in item.items() if v not in ["", 0]}


# ---------- main pipeline ----------
def sync_publications(journal_csv_url: str, conf_csv_url: str):
    # Journals tab -> _data/pub_journal.yml
    journal_rows = fetch_csv_rows(journal_csv_url)
    journals: List[Dict[str, Any]] = []
    for row in journal_rows:
        item = journal_item(row)
        if item:
            journals.append(item)
    dump_yaml(journals, "_data/pub_journal.yml")

    # Conferences tab -> split by type -> _data/pub_conf_int.yml / _data/pub_conf_dom.yml
    conf_rows = fetch_csv_rows(conf_csv_url)
    conf_int: List[Dict[str, Any]] = []
    conf_dom: List[Dict[str, Any]] = []

    for row in conf_rows:
        t = norm(row.get("type")).lower()
        item = conf_item(row)
        if not item:
            continue

        if t == "conf_international":
            conf_int.append(item)
        elif t == "conf_domestic":
            conf_dom.append(item)
        else:
            # ignore unknown types to avoid dirty data
            continue

    dump_yaml(conf_int, "_data/pub_conf_int.yml")
    dump_yaml(conf_dom, "_data/pub_conf_dom.yml")

    # Hard fail if nothing parsed: prevents “No changes” silently hiding issues
    if len(journals) + len(conf_int) + len(conf_dom) == 0:
        raise SystemExit("No publications parsed. Check CSV headers / URLs / type values.")


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/sync_from_gsheets_tabs.py <journal_csv_url> <conf_csv_url>")
        sys.exit(1)

    journal_csv_url = sys.argv[1]
    conf_csv_url = sys.argv[2]

    sync_publications(journal_csv_url, conf_csv_url)

if __name__ == "__main__":
    main()
