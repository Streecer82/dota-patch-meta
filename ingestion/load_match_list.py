"""
Page back through /proMatches until the 7.37 release, saving each page to the raw schema.

Resumable: if earlier pages are already saved, carries on below the smallest match ID saved.

Run from the project root:
    python ingestion/load_match_list.py
"""

from datetime import datetime, timezone

from api import get_json
from warehouse import get_connection, create_raw_table, save_response, RAW_SCHEMA

TABLE_NAME = "pro_matches"
ENDPOINT = "/proMatches"
# Patch 7.37 (patch ID 56) was released on 2024-08-01: the start of the project's scope.
CUTOFF_UTC = datetime(2024, 8, 1, tzinfo=timezone.utc)


def find_resume_point(con):
    """Return (smallest match_id, oldest start_time) already saved, or (None, None) if nothing is saved."""
    return con.execute(f"""
        SELECT
            MIN(match ->> 'match_id')::bigint AS smallest_match_id,
            MIN(match ->> 'start_time')::bigint AS oldest_start_time
            FROM {RAW_SCHEMA}.{TABLE_NAME},
            UNNEST(response::json[]) AS matches(match)
            """).fetchone()


def load_match_list(max_pages=None):
    """Fetch pages of pro matches, newest to oldest, until the cutoff or max_pages."""
    con = get_connection()
    create_raw_table(con, TABLE_NAME)
    cutoff_timestamp = CUTOFF_UTC.timestamp()

    smallest_match_id, oldest_start_time = find_resume_point(con)

    if oldest_start_time is not None and oldest_start_time < cutoff_timestamp:
        print("Backfill already complete: saved matches already reach the cutoff date.")
        con.close()
        return
    if smallest_match_id is None:
        params = None
        print("No pages saved yet: starting from the newest matches")
    else:
        params = {"less_than_match_id": smallest_match_id}
        print(f"Resuming below match_id {smallest_match_id}")

    page_number = 0
    while True:
        page_number += 1

        page = get_json(ENDPOINT, params)
        if not page:
            print("Empty page: no older matches available.")
            break
        save_response(con, TABLE_NAME, ENDPOINT, params, page)

        page_smallest_id = min(m["match_id"] for m in page)
        page_oldest_time = min(m["start_time"] for m in page)
        oldest_date = datetime.fromtimestamp(page_oldest_time, tz=timezone.utc).date()
        print(f"Page {page_number}: {len(page)} matches, oldest {oldest_date}")

        if page_oldest_time < cutoff_timestamp:
            print(f"Reached the cutoff ({CUTOFF_UTC.date()}).")
            break

        if max_pages is not None and page_number >= max_pages:
            print(f"Stopped after {max_pages} pages (max_pages).")
            break

        params = {"less_than_match_id": page_smallest_id}

    con.close()


if __name__ == "__main__":
    load_match_list()