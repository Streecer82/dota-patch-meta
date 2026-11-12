"""
Stage 3: explore the OpenDota API.

Calls each endpoint once and saves the raw response as a JSON file in
data/samples/, so the data can be inspected and profiled before any
modelling decisions are made.

Run from the project root, with the virtual environment active:
    python ingestion/explore_api.py
"""

import json
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------------
# Paths are built from this file's location, not the folder you run it
# from, so the script works on any computer and from any folder.
#   __file__            -> .../dota-patch-meta/ingestion/explore_api.py
#   .parent             -> .../dota-patch-meta/ingestion
#   .parent.parent      -> .../dota-patch-meta   (the project root)
# ---------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLES_DIR = PROJECT_ROOT / "data" / "samples"

BASE_URL = "https://api.opendota.com/api"

# Endpoints to sample: (file name to save as, path after BASE_URL)
ENDPOINTS = [
    ("pro_matches", "/proMatches"),
    ("heroes", "/constants/heroes"),
    ("patches", "/constants/patch"),
    ("pro_players", "/proPlayers"),
    ("teams", "/teams"),
    ("leagues", "/leagues"),
    ("items", "/constants/items"),
    ("items_ids", "/constants/item_ids"),
]


def get_json(path):
    """Call one endpoint and return the parsed JSON. Stops on any HTTP error."""
    url = BASE_URL + path
    print(f"Calling {url}")
    response = requests.get(url, timeout=30)
    response.raise_for_status()   # raises an error for 4xx / 5xx responses
    return response.json()


def save_json(data, name):
    """Save data as pretty-printed JSON in data/samples/<name>.json."""
    file_path = SAMPLES_DIR / f"{name}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    size = len(data) if isinstance(data, (list, dict)) else "n/a"
    print(f"  saved {file_path.name} ({size} top-level items)")


def main():
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. The list and reference endpoints
    for name, path in ENDPOINTS:
        data = get_json(path)
        save_json(data, name)
        time.sleep(1.5)   # stay well under the free limit of ~60 calls a minute

    # 2. Full detail for a few recent pro matches.
    #    Taken from the pro_matches list we just saved.
    with open(SAMPLES_DIR / "pro_matches.json", encoding="utf-8") as f:
        pro_matches = json.load(f)

    for match in pro_matches[:10]:
        match_id = match["match_id"]
        detail = get_json(f"/matches/{match_id}")
        save_json(detail, f"match_{match_id}")
        time.sleep(1.5)

    print("Done. Samples are in data/samples/")


if __name__ == "__main__":
    main()
