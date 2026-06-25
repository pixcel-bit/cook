#!/usr/bin/env python3
"""Fetch Pexels images for each recipe in menu.json.

Rules:
- If a recipe exists in preferences.json with good_count > 0 and photo_url,
  reuse that URL without calling the API.
- Otherwise fetch from Pexels API.
- After fetching, if a recipe has good_count > 0, persist photo_url back to
  preferences.json so it can be reused in future weeks.
- KEYWORD_MAP translates Japanese recipe names to English search terms.
  Add new entries here whenever new recipes are generated.
"""
import json
import os
import sys

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "requests"])
    import requests

API_KEY = os.environ.get("PEXELS_API_KEY", "")
if not API_KEY:
    print("ERROR: PEXELS_API_KEY not set", file=sys.stderr)
    sys.exit(1)

ROOT = os.path.join(os.path.dirname(__file__), "..")
MENU_PATH = os.path.join(ROOT, "menu.json")
PREFS_PATH = os.path.join(ROOT, "preferences.json")

# Japanese recipe name → English search keyword.
# Extend this map each week for new recipes.
KEYWORD_MAP = {
    "鶏肉のふんわりハンバーグ 和風きのこあん": "japanese chicken hamburger steak mushroom sauce",
    "鶏もものトマト煮込み（ビストロ）": "chicken tomato stew japanese",
    "てりやき豚こまボール（ビストロ）": "pork teriyaki meatball",
    "鶏もものねぎ塩蒸し（ビストロ）": "steamed chicken green onion salt",
    "カリッと豚こまの揚げ焼き にんにく醤油": "crispy pork garlic soy sauce japanese",
    "いわし缶とキャベツのさっぱり和風煮": "sardine cabbage japanese simmered",
    "しいたけとエリンギのごまマリネ": "mushroom sesame marinade japanese",
    "レタスとえのきのさっぱりナムル": "lettuce mushroom namul korean salad",
    "絹豆腐の薬味たっぷり冷奴": "cold tofu yakumi japanese",
}


def fetch_pexels(query: str) -> dict | None:
    """Call Pexels API and return image info, or None on failure."""
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "per_page": 1, "orientation": "square"},
            headers={"Authorization": API_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if not photos:
            return None
        p = photos[0]
        return {
            "url": p["src"]["medium"],
            "photographer": p["photographer"],
            "photographer_url": p["photographer_url"],
            "pexels_url": p["url"],
        }
    except Exception as e:
        print(f"  WARN: API call failed for '{query}': {e}", file=sys.stderr)
        return None


def main():
    with open(MENU_PATH, encoding="utf-8") as f:
        menu = json.load(f)
    with open(PREFS_PATH, encoding="utf-8") as f:
        prefs = json.load(f)

    # Build lookup: name → recipe dict (for recipes with good_count > 0)
    saved_photos = {
        r["name"]: r.get("photo_url", "")
        for r in prefs.get("recipes", [])
        if r.get("good_count", 0) > 0 and r.get("photo_url")
    }
    # Build lookup: name → recipe dict for all recipes (to update photo_url)
    prefs_by_name = {r["name"]: r for r in prefs.get("recipes", [])}

    prefs_dirty = False

    for recipe in menu.get("main", []) + menu.get("side", []):
        name = recipe["name"]
        recipe.pop("svg", None)

        # Reuse saved photo if available
        if name in saved_photos:
            print(f"Reusing saved photo: {name}")
            recipe["image"] = saved_photos[name]
            recipe["image_credit"] = prefs_by_name[name].get("photo_credit", {})
            continue

        # Fetch from Pexels
        keyword = KEYWORD_MAP.get(name, name)
        print(f"Fetching: {name} → '{keyword}'")
        result = fetch_pexels(keyword)

        if result:
            recipe["image"] = result["url"]
            recipe["image_credit"] = {
                "photographer": result["photographer"],
                "photographer_url": result["photographer_url"],
                "pexels_url": result["pexels_url"],
            }
            print(f"  ✓ {result['url'][:60]}...")

            # Persist photo_url to prefs if this recipe is liked
            if name in prefs_by_name and prefs_by_name[name].get("good_count", 0) > 0:
                prefs_by_name[name]["photo_url"] = result["url"]
                prefs_by_name[name]["photo_credit"] = recipe["image_credit"]
                prefs_dirty = True
                print(f"  → saved to preferences (good_count > 0)")
        else:
            recipe["image"] = ""
            recipe["image_credit"] = {}
            print(f"  ✗ no image found")

    with open(MENU_PATH, "w", encoding="utf-8") as f:
        json.dump(menu, f, ensure_ascii=False, indent=2)
    print("\nmenu.json updated.")

    if prefs_dirty:
        with open(PREFS_PATH, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
        print("preferences.json updated (photo_url saved).")


if __name__ == "__main__":
    main()
