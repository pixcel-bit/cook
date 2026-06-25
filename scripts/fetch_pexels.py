#!/usr/bin/env python3
"""Fetch Pexels images for each recipe in menu.json and update the file."""
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

# Japanese recipe name → English search keyword
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
    """Return {url, photographer, photographer_url} or None on failure."""
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
        print(f"  WARN: failed for '{query}': {e}", file=sys.stderr)
        return None


def main():
    menu_path = os.path.join(os.path.dirname(__file__), "..", "menu.json")
    with open(menu_path, encoding="utf-8") as f:
        menu = json.load(f)

    for recipe in menu.get("main", []) + menu.get("side", []):
        name = recipe["name"]
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
        else:
            recipe["image"] = ""
            recipe["image_credit"] = {}
            print(f"  ✗ no image found")

        # Remove svg field
        recipe.pop("svg", None)

    with open(menu_path, "w", encoding="utf-8") as f:
        json.dump(menu, f, ensure_ascii=False, indent=2)

    print("\nDone. menu.json updated.")


if __name__ == "__main__":
    main()
