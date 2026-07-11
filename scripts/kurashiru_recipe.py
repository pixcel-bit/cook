#!/usr/bin/env python3
"""Fetch the FACTUAL recipe data from a kurashiru recipe page (JSON-LD).

Purpose: ground the weekly menu's steps in the ACTUAL popular recipe
(real ingredient amounts, technique, order, times) instead of generic
invention — while the routine still writes the published steps in its OWN
words (see CLAUDE.md Step 5). Facts like quantities/times/technique are not
copyrightable; the site's step *wording* is, so it must NOT be copied or
lightly reworded into menu.json.

Usage:
  python3 scripts/kurashiru_recipe.py <kurashiru_recipe_url>

Output (stdout, JSON): name, recipeYield, totalTime, recipeIngredient[],
recipeInstructions[] — for the routine to read as reference only.
Needs kurashiru.com on the environment network allowlist.
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
LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def fetch(url: str) -> str | None:
    for attempt in range(4):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
            r.raise_for_status()
            return r.text
        except Exception as e:
            print(f"  WARN: fetch failed ({attempt+1}/4): {e}", file=sys.stderr)
            time.sleep(2 ** attempt)
    return None


def instr_text(ri):
    out = []
    if isinstance(ri, list):
        for step in ri:
            if isinstance(step, dict):
                out.append(step.get("text") or step.get("name") or "")
            else:
                out.append(str(step))
    elif isinstance(ri, str):
        out = [ri]
    return [s.strip() for s in out if s and s.strip()]


def main():
    if len(sys.argv) != 2:
        print("usage: python3 scripts/kurashiru_recipe.py <url>", file=sys.stderr)
        sys.exit(2)
    url = sys.argv[1]
    html = fetch(url)
    if not html:
        print(json.dumps({"url": url, "error": "unreachable"}, ensure_ascii=False))
        sys.exit(1)
    recipe = None
    for block in LD_RE.findall(html):
        try:
            data = json.loads(block)
        except Exception:
            continue
        for it in (data if isinstance(data, list) else [data]):
            if isinstance(it, dict) and it.get("@type") == "Recipe":
                recipe = it
                break
        if recipe:
            break
    if not recipe:
        print(json.dumps({"url": url, "error": "no Recipe JSON-LD"}, ensure_ascii=False))
        sys.exit(1)
    out = {
        "url": url,
        "name": recipe.get("name"),
        "recipeYield": recipe.get("recipeYield"),
        "totalTime": recipe.get("totalTime") or recipe.get("cookTime"),
        "recipeIngredient": recipe.get("recipeIngredient", []),
        "recipeInstructions": instr_text(recipe.get("recipeInstructions", [])),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
