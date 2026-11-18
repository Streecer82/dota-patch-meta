"""
Fetch the full detail for every sampled match into raw_opendota.match_details.

Resumable: each run only fetches sampled matches that have no detail saved yet.
A failure for one match (e.g. 404) is recorded and skipped; if the API keeps
refusing (rate limit), the run stops and can simply be run again later.

Run from the project root:
    python ingestion/load_match_details.py
"""

import requests

from api import get_json
from warehouse import get_connection, create_raw_table, save_response, RAW_SCHEMA

TABLE_NAME = "match_details"
FAILURES_TABLE = "match_detail_failures"
PROGRESS_EVERY = 50

def create_failures_table(con):
    """One row per sampled match whose detail couldn't be fetched."""
    con.execute(f"""
        create table if not exists {RAW_SCHEMA}.{FAILURES_TABLE} (
            failed_at  timestamp,
            match_id   bigint,
            error      varchar
        )
    """)

def find_remaining_matches(con):
    """Sampled match IDs with no detail saved and no recorded failure, in a fixed order."""
    rows = con.execute(f"""
        select s.match_id
        from {RAW_SCHEMA}.match_sample as s
        where not exists (
            select 1
            from {RAW_SCHEMA}.{TABLE_NAME} as d
            where (d.response ->> 'match_id')::bigint = s.match_id
        )
        and not exists (
            select 1
            from {RAW_SCHEMA}.{FAILURES_TABLE} as f
            where f.match_id = s.match_id
        )
        order by s.patch_id, s.match_id
    """).fetchall()
    return [row[0] for row in rows]

def load_match_details(max_matches=None):
    """Fetch details for remaining sampled matches, up to max_matches if given."""
    con = get_connection()
    create_raw_table(con, TABLE_NAME)
    create_failures_table(con)

    remaining = find_remaining_matches(con)
    print(f"{len(remaining)} sampled matches still need details.")

    if max_matches is not None:
        remaining = remaining[:max_matches]
        print(f"This run is limited to {len(remaining)}.")

    saved = 0
    failed = 0

    for number, match_id in enumerate(remaining, start=1):
        path = f"/matches/{match_id}"
        try:
            data = get_json(path)
        except requests.HTTPError as error:
            # A problem with this one match (e.g. 404): record it and move on.
            con.execute(
                f"insert into {RAW_SCHEMA}.{FAILURES_TABLE} values "
                f"(current_timestamp at time zone 'UTC', ?, ?)",
                [match_id, str(error)],
            )
            failed += 1
            print(f"  Match {match_id} failed: {error}")
            continue

        save_response(con, TABLE_NAME, path, None, data)
        saved += 1

        if number % PROGRESS_EVERY == 0:
            print(f"Progress: {number} of {len(remaining)} done ({failed} failed)")

    print(f"Finished: {saved} saved, {failed} failed.")
    con.close()


if __name__ == "__main__":
    load_match_details()