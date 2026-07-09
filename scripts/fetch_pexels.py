#!/usr/bin/env python3
"""Fetch a photo for each recipe in menu.json.

Source tiers (accuracy over aesthetics):
1. Openverse  — search the JAPANESE dish name (image_query_ja, falling back
   to a cleaned recipe name). CC-licensed photos of actual Japanese home
   dishes; far more pinpoint than translated English keywords.
2. Wikimedia Commons — same Japanese query.
3. Unsplash — legacy fallback using the English search_keyword field.

Tiers 1–2 need no API key or account. If a tier's host is unreachable
(e.g. blocked by the environment's network policy) it fails soft and the
next tier is tried, so the worst case equals the old Unsplash behaviour.

Rules:
- If a recipe exists in preferences.json with good_count > 0 and photo_url,
  reuse that URL without calling any API.
- After fetching, if a recipe has good_count > 0, persist photo_url back to
  preferences.json so it can be reused in future weeks.
"""
from __future__ import annotations
import json
import os
import re
import sys
import time

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "requests"])
    import requests

API_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")
if not API_KEY:
    print("ERROR: UNSPLASH_ACCESS_KEY not set", file=sys.stderr)
    sys.exit(1)

ROOT = os.path.join(os.path.dirname(__file__), "..")
MENU_PATH = os.path.join(ROOT, "menu.json")
PREFS_PATH = os.path.join(ROOT, "preferences.json")

IMG_EXT = re.compile(r"\.(jpe?g|png|webp)$", re.I)


def derive_ja_query(recipe: dict) -> str:
    """Japanese search query: image_query_ja if present, else the recipe
    name stripped of prep-style prefixes and parentheticals."""
    q = (recipe.get("image_query_ja") or "").strip()
    if q:
        return q
    name = recipe.get("name", "")
    name = re.sub(r"[（(].*?[)）]", "", name)          # （成形冷凍） etc.
    name = re.sub(r"下味冷凍|作り置き", "", name)
    return name.strip()


def fetch_openverse(query: str, exclude_urls: set | None = None) -> list[dict]:
    """Search Openverse (CC images, no API key). Returns [] on any failure."""
    try:
        resp = requests.get(
            "https://api.openverse.org/v1/images/",
            params={"q": query, "page_size": 10, "mature": "false"},
            headers={"User-Agent": "cook-menu-app/1.0"},
            timeout=12,
        )
        resp.raise_for_status()
        results = []
        for p in resp.json().get("results", []):
            url = p.get("url") or p.get("thumbnail") or ""
            if not url or (exclude_urls and url in exclude_urls):
                continue
            if not IMG_EXT.search(url.split("?")[0]) and not p.get("thumbnail"):
                continue
            lic = (p.get("license") or "").upper()
            ver = p.get("license_version") or ""
            results.append({
                "url": url,
                "photographer": p.get("creator") or "unknown",
                "photographer_url": p.get("creator_url") or p.get("foreign_landing_url") or "",
                "unsplash_url": p.get("foreign_landing_url") or url,
                "source": "Openverse",
                "license": (lic + " " + ver).strip(),
            })
        return results
    except Exception as e:
        print(f"  WARN: Openverse failed for '{query}': {e}", file=sys.stderr)
        return []


def fetch_wikimedia(query: str, exclude_urls: set | None = None) -> list[dict]:
    """Search Wikimedia Commons file pages (no API key). Returns [] on failure."""
    try:
        resp = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query", "format": "json",
                "generator": "search", "gsrsearch": query,
                "gsrnamespace": 6, "gsrlimit": 10,
                "prop": "imageinfo", "iiprop": "url|extmetadata",
                "iiurlwidth": 1080,
            },
            headers={"User-Agent": "cook-menu-app/1.0"},
            timeout=12,
        )
        resp.raise_for_status()
        pages = (resp.json().get("query") or {}).get("pages") or {}
        results = []
        for p in pages.values():
            info = (p.get("imageinfo") or [{}])[0]
            url = info.get("thumburl") or info.get("url") or ""
            if not url or not IMG_EXT.search(url.split("?")[0]):
                continue
            if exclude_urls and url in exclude_urls:
                continue
            meta = info.get("extmetadata") or {}
            artist = re.sub(r"<[^>]+>", "", (meta.get("Artist") or {}).get("value", "")).strip() or "unknown"
            results.append({
                "url": url,
                "photographer": artist,
                "photographer_url": info.get("descriptionurl") or "",
                "unsplash_url": info.get("descriptionurl") or url,
                "source": "Wikimedia Commons",
                "license": (meta.get("LicenseShortName") or {}).get("value", ""),
            })
        return results
    except Exception as e:
        print(f"  WARN: Wikimedia failed for '{query}': {e}", file=sys.stderr)
        return []


def fetch_unsplash(keyword: str, exclude_urls: set | None = None) -> list[dict]:
    """Return up to 5 image dicts from Unsplash (excluding already-used URLs), or [] on failure."""
    for attempt in range(3):
        try:
            resp = requests.get(
                "https://api.unsplash.com/search/photos",
                params={"query": keyword, "per_page": 10, "orientation": "squarish"},
                headers={"Authorization": f"Client-ID {API_KEY}"},
                timeout=10,
            )
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 60))
                print(f"  WARN: rate limited, waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            results = []
            for p in resp.json().get("results", []):
                url = p["urls"]["regular"]
                if exclude_urls and url in exclude_urls:
                    continue
                results.append({
                    "url": url,
                    "photographer": p["user"]["name"],
                    "photographer_url": p["user"]["links"]["html"],
                    "unsplash_url": p["links"]["html"],
                    "source": "Unsplash",
                    "license": "",
                })
            return results
        except Exception as e:
            print(f"  WARN: API call failed for '{keyword}': {e}", file=sys.stderr)
            if attempt < 2:
                time.sleep(2 ** attempt)
    return []


def fetch_unsplash_with_fallback(keyword: str, exclude_urls: set | None = None) -> tuple[list[dict], str]:
    """Fetch from Unsplash; skip already-used URLs; retry with shorter keyword if 0 results.
    Returns (results, used_keyword).
    """
    results = fetch_unsplash(keyword, exclude_urls)
    if results:
        return results, keyword

    # Fallback: drop words from the end one by one
    words = keyword.split()
    for n in range(len(words) - 1, 1, -1):
        shorter = " ".join(words[:n])
        print(f"  → fallback keyword: '{shorter}'")
        results = fetch_unsplash(shorter, exclude_urls)
        if results:
            return results, shorter

    return [], keyword


def main():
    with open(MENU_PATH, encoding="utf-8") as f:
        menu = json.load(f)
    with open(PREFS_PATH, encoding="utf-8") as f:
        prefs = json.load(f)

    # Build lookup: name → saved photo info (liked recipes only)
    saved_photos = {
        r["name"]: {"url": r["photo_url"], "credit": r.get("photo_credit", {})}
        for r in prefs.get("recipes", [])
        if r.get("good_count", 0) > 0 and r.get("photo_url")
    }
    prefs_by_name = {r["name"]: r for r in prefs.get("recipes", [])}

    prefs_dirty = False
    used_urls: set = set()

    for recipe in menu.get("main", []) + menu.get("side", []):
        name = recipe["name"]

        # Reuse saved photo for liked recipes
        if name in saved_photos:
            saved = saved_photos[name]
            recipe["image"] = saved["url"]
            recipe["image_credit"] = saved["credit"]
            used_urls.add(saved["url"])
            print(f"Reusing saved photo: {name}")
            continue

        # Tier 1–2: Japanese dish name on Openverse / Wikimedia (pinpoint),
        # Tier 3: legacy Unsplash English keyword (aesthetic but generic).
        ja = derive_ja_query(recipe)
        results: list[dict] = []
        if ja:
            print(f"Fetching: {name} → ja:'{ja}'")
            results = fetch_openverse(ja, exclude_urls=used_urls)
            if results:
                print("  ✓ via Openverse")
            else:
                results = fetch_wikimedia(ja, exclude_urls=used_urls)
                if results:
                    print("  ✓ via Wikimedia Commons")
        if not results:
            keyword = recipe.get("search_keyword") or name
            print(f"  → fallback Unsplash: '{keyword}'")
            results, used_keyword = fetch_unsplash_with_fallback(keyword, exclude_urls=used_urls)

        if results:
            p = results[0]
            recipe["image"] = p["url"]
            recipe["image_credit"] = {
                "photographer": p["photographer"],
                "photographer_url": p["photographer_url"],
                "unsplash_url": p["unsplash_url"],
                "source": p.get("source", "Unsplash"),
                "license": p.get("license", ""),
            }
            used_urls.add(p["url"])
            print(f"  ✓ photo fetched")

            # Persist to prefs if this recipe is liked
            if name in prefs_by_name and prefs_by_name[name].get("good_count", 0) > 0:
                prefs_by_name[name]["photo_url"] = p["url"]
                prefs_by_name[name]["photo_credit"] = recipe["image_credit"]
                prefs_dirty = True
                print(f"  → saved to preferences (good_count > 0)")
        else:
            recipe["image"] = ""
            recipe["image_credit"] = {}
            print(f"  ✗ no images found")

    with open(MENU_PATH, "w", encoding="utf-8") as f:
        json.dump(menu, f, ensure_ascii=False, indent=2)
    print("\nmenu.json updated.")

    if prefs_dirty:
        with open(PREFS_PATH, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
        print("preferences.json updated (photo_url saved).")


if __name__ == "__main__":
    main()
