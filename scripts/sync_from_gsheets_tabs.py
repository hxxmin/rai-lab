import csv
import io
import re
import sys
from typing import Dict, List, Any, Optional

import requests
import yaml
from datetime import datetime

MONTH_ABBR = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

def parse_date_yyyy_mm_dd(s: str) -> datetime:
    # expects "YYYY-MM-DD"
    return datetime.strptime(norm(s), "%Y-%m-%d")

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
def news_item(row: Dict[str, str]) -> Optional[Dict[str, Any]]:
    ds = norm(row.get("date"))
    if not ds:
        return None

    try:
        dt = parse_date_yyyy_mm_dd(ds)
    except ValueError:
        # date가 깨지면 스킵(원하면 에러로 바꿀 수 있음)
        return None

    item: Dict[str, Any] = {
        "year": dt.year,
        "month": MONTH_ABBR[dt.month - 1],
        "date": ds,  # YAML에서 2025-10-11 형태로 쓰려면 문자열이 제일 안전
        "type": norm(row.get("type")),
        "content": norm(row.get("content")),
    }
    return {k: v for k, v in item.items() if v not in ["", 0]}

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

def project_item(row: Dict[str, str]) -> Optional[Dict[str, Any]]:
    year = to_int_year(row.get("year"))
    title = norm(row.get("title"))
    if not year or not title:
        return None

    item: Dict[str, Any] = {
        "year": year,
        "title": title,
        "period": norm(row.get("period")),
        "funder": norm(row.get("funder")),
    }
    return {k: v for k, v in item.items() if v not in ["", 0]}

def patent_item(row: Dict[str, str]) -> Optional[Dict[str, Any]]:
    year = to_int_year(row.get("year"))
    title = norm(row.get("title"))
    if not year or not title:
        return None

    item: Dict[str, Any] = {
        "year": year,
        "title": title,
        "authors": norm(row.get("authors")),
        "registration": norm(row.get("registration")),
        "application": norm(row.get("application")),
    }
    return {k: v for k, v in item.items() if v not in ["", 0]}

# ---------- main pipeline ----------
def sync_news(news_csv_url: str):
    rows = fetch_csv_rows(news_csv_url)
    items: List[Dict[str, Any]] = []

    for row in rows:
        item = news_item(row)
        if item:
            items.append(item)

    # 최신 날짜 먼저
    items.sort(key=lambda x: x.get("date", ""), reverse=True)

    dump_yaml(items, "_data/news.yml")

    if len(items) == 0:
        raise SystemExit("No news parsed. Check news CSV header/URL/date format.")


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

def sync_projects(project_csv_url: str):
    rows = fetch_csv_rows(project_csv_url)
    projects: List[Dict[str, Any]] = []

    for row in rows:
        item = project_item(row)
        if item:
            projects.append(item)

    projects.sort(key=lambda x: (x.get("year", 0), x.get("title", "")), reverse=True)
    dump_yaml(projects, "_data/projects.yml")

    if len(projects) == 0:
        raise SystemExit("No projects parsed. Check project CSV header/URL.")
    
def sync_patents(patent_csv_url: str):
    rows = fetch_csv_rows(patent_csv_url)
    patents: List[Dict[str, Any]] = []

    for row in rows:
        item = patent_item(row)
        if item:
            patents.append(item)

    # 최신 먼저 정렬
    patents.sort(key=lambda x: (x.get("year", 0), x.get("title", "")), reverse=True)

    dump_yaml(patents, "_data/patent.yml")

    if len(patents) == 0:
        raise SystemExit("No patents parsed. Check patent CSV header/URL.")

def main():
    if len(sys.argv) != 6:
        print("Usage: python scripts/sync_from_gsheets_tabs.py <journal_csv_url> <conf_csv_url> <patent_csv_url> <project_csv_url> <news_csv_url>")
        sys.exit(1)

    journal_csv_url = sys.argv[1]
    conf_csv_url = sys.argv[2]
    patent_csv_url = sys.argv[3]
    project_csv_url = sys.argv[4]
    news_csv_url = sys.argv[5]

    sync_publications(journal_csv_url, conf_csv_url)
    sync_patents(patent_csv_url)
    sync_projects(project_csv_url)
    sync_news(news_csv_url)


if __name__ == "__main__":
    main()
