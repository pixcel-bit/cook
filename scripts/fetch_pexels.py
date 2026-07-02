#!/usr/bin/env python3
"""Fetch Unsplash images for each recipe in menu.json.

Rules:
- If a recipe exists in preferences.json with good_count > 0 and photo_url,
  reuse that URL without calling the API.
- Otherwise fetch top 3 results from Unsplash using recipe's search_keyword field.
- After fetching, if a recipe has good_count > 0, persist photo_url back to
  preferences.json so it can be reused in future weeks.
"""
from __future__ import annotations
import json
import os
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

        # Fetch from Unsplash, skipping URLs already used by other recipes
        keyword = recipe.get("search_keyword") or name
        print(f"Fetching: {name} → '{keyword}'")
        results, used_keyword = fetch_unsplash_with_fallback(keyword, exclude_urls=used_urls)

        if results:
            p = results[0]
            recipe["image"] = p["url"]
            recipe["image_credit"] = {
                "photographer": p["photographer"],
                "photographer_url": p["photographer_url"],
                "unsplash_url": p["unsplash_url"],
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
