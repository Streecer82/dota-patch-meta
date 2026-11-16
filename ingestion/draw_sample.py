"""
Draw a reproducible sample of matches per patch into raw_opendota.match_sample.

The table is created only once: rerunning this script never draws a new sample.
To redraw on purpose, drop the table first.

Run from the project root:
    python ingestion/draw_sample.py
"""

from warehouse import get_connection, RAW_SCHEMA

SAMPLE_SEED = 42
MATCHES_PER_PATCH = 1000
FIRST_PATCH_ID = 56   # 7.37, released 2024-08-01
LAST_PATCH_ID = 60    # 7.41, current

SAMPLE_SQL = f"""
create table if not exists {RAW_SCHEMA}.match_sample as
with patches as (
    select
        (patch ->> 'id')::bigint                            as patch_id,
        patch ->> 'name'                                    as patch_name,
        (patch ->> 'date')::timestamptz at time zone 'UTC'  as patch_date
    from {RAW_SCHEMA}.patches as p,
         unnest(response::json[]) as patches(patch)
    where (patch ->> 'id')::bigint between {FIRST_PATCH_ID} and {LAST_PATCH_ID}
    qualify p.loaded_at = max(p.loaded_at) over ()
),
patch_windows as (
    select
        patch_id,
        patch_name,
        patch_date as valid_from,
        coalesce(lead(patch_date) over (order by patch_date),
                 timestamp '2100-01-01') as valid_to
    from patches
),
matches as (
    select distinct
        (match ->> 'match_id')::bigint                                    as match_id,
        to_timestamp((match ->> 'start_time')::bigint) at time zone 'UTC' as match_started_utc
    from {RAW_SCHEMA}.pro_matches,
         unnest(response::json[]) as page_matches(match)
),
matches_with_patch as (
    select m.match_id, m.match_started_utc, pw.patch_id, pw.patch_name
    from matches as m
    join patch_windows as pw
      on  m.match_started_utc >= pw.valid_from
      and m.match_started_utc <  pw.valid_to
)
select
    match_id,
    patch_id,
    patch_name,
    match_started_utc,
    {SAMPLE_SEED}                         as sample_seed,
    current_timestamp at time zone 'UTC'  as sampled_at
from matches_with_patch
qualify row_number() over (
    partition by patch_id
    order by md5(concat(match_id, ':', {SAMPLE_SEED}))
) <= {MATCHES_PER_PATCH}
"""

def draw_sample():
    """Create the sample table (first run only) and print how many matches each patch has."""
    con = get_connection()
    con.execute(SAMPLE_SQL)

    rows = con.execute(f"""
        select patch_id, patch_name, count(*) as matches, min(sampled_at) as sampled_at
        from {RAW_SCHEMA}.match_sample
        group by patch_id, patch_name
        order by patch_id
    """).fetchall()

    for patch_id, patch_name, matches, sampled_at in rows:
        print(f"Patch {patch_id} ({patch_name}): {matches} matches, sampled at {sampled_at}")

    con.close()


if __name__ == "__main__":
    draw_sample()