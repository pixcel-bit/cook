#!/usr/bin/env python3
"""Rank kurashiru recipe URLs by popularity (保存数) for menu selection.

The weekly routine collects candidate recipe names+URLs via WebSearch, then
passes the kurashiru.com URLs here to get a quantitative popularity signal.
Each recipe page's raw HTML embeds:
  - bookmark-count  (保存数 — the primary popularity metric)
  - ratingValue / ratingCount  (star rating, from JSON-LD aggregateRating)

Usage:
  python3 scripts/kurashiru_rank.py <url1> <url2> ...
  echo "<url-per-line>" | python3 scripts/kurashiru_rank.py

Output: JSON array to stdout, sorted by bookmark_count desc:
  [{"url","bookmark_count","rating_value","rating_count"}, ...]
Unreachable / non-kurashiru / unparseable URLs get null counts and sort last.
Needs kurashiru.com + www.kurashiru.com on the environment network allowlist.
"""
from __future__ import annotations
import json
import re
import sys
import time

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "requests"])
    import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
BM_RE = re.compile(r'bookmark-count"\s*:\s*(\d+)')
RV_RE = re.compile(r'"ratingValue"\s*:\s*"?([\d.]+)')
RC_RE = re.compile(r'"ratingCount"\s*:\s*"?(\d+)')


def fetch(url: str) -> str | None:
    for attempt in range(4):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
            r.raise_for_status()
            return r.text
        except Exception as e:
            print(f"  WARN: fetch failed ({attempt+1}/4) {url}: {e}", file=sys.stderr)
            time.sleep(2 ** attempt)
    return None


def rank(url: str) -> dict:
    out = {"url": url, "bookmark_count": None, "rating_value": None, "rating_count": None}
    if "kurashiru.com" not in url:
        return out
    html = fetch(url)
    if not html:
        return out
    bm = BM_RE.search(html)
    rv = RV_RE.search(html)
    rc = RC_RE.search(html)
    if bm:
        out["bookmark_count"] = int(bm.group(1))
    if rv:
        out["rating_value"] = float(rv.group(1))
    if rc:
        out["rating_count"] = int(rc.group(1))
    return out


def main():
    args = sys.argv[1:]
    if not args and not sys.stdin.isatty():
        args = [ln.strip() for ln in sys.stdin if ln.strip()]
    if not args:
        print("usage: python3 scripts/kurashiru_rank.py <url> [<url> ...]", file=sys.stderr)
        sys.exit(2)
    results = [rank(u) for u in args]
    results.sort(key=lambda r: (r["bookmark_count"] is None, -(r["bookmark_count"] or 0)))
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
