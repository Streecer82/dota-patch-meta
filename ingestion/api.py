"""
Calling the OpenDota API.

Other ingestion scripts import get_json fro here, so every API call in the project goes through the same
rate limiting and retries
"""

import time

import requests

BASE_URL = "https://api.opendota.com/api"
PAUSE_SECONDS = 1.0
MAX_ATTEMPTS = 5
FIRST_RETRY_WAIT_SECONDS = 5.0


def get_json(path,params=None):
    """Call an OpenDota endpoint and return the parsed JSON."""
    url = BASE_URL + path

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"Calling {url} {params or ''} (attempt {attempt} of {MAX_ATTEMPTS})")
        time.sleep(PAUSE_SECONDS)
        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 200:
            return response.json()

        elif response.status_code == 429 or 500 <= response.status_code <= 599:
            if attempt < MAX_ATTEMPTS:
                wait = FIRST_RETRY_WAIT_SECONDS * 2 ** (attempt - 1)
                print(f" Got {response.status_code}; waiting {wait}s before retrying:)")
                time.sleep(wait)

        else:
            response.raise_for_status()
            raise RuntimeError(f"Unexpected status {response.status_code} from {url}")
    raise RuntimeError(
        f"Gave up on {url} after {MAX_ATTEMPTS} attempts "
        f"(last status {response.status_code})"
    )



if __name__ == "__main__":
    heroes = get_json("/constants/heroes")
    print(f"Heroes returned: {len(heroes)}")

    page = get_json("/proMatches", params={"less_than_match_id": 8000000000})
    print(f"Matches on page: {len(page)}")

    get_json("/this-does-not-exist")