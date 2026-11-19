{{ config(materialized='table') }}

with base as (

    select * from {{ ref("base_opendota__match_details") }}

),

parsed as ( 
    
    select
        match_id,
        loaded_at_utc,
        json_transform(response, '{
            "start_time":    "BIGINT",
            "duration":      "BIGINT",
            "patch":         "INTEGER",
            "leagueid":      "BIGINT",
            "radiant_win":   "BOOLEAN",
            "radiant_score": "INTEGER",
            "dire_score":    "INTEGER",
            "radiant_team_id": "BIGINT",
            "dire_team_id": "BIGINT",
            "radiant_name": "VARCHAR",
            "dire_name": "VARCHAR",  
            "objectives":    ["JSON"]
        }') as m
    from base

),

matches as (

    select
        match_id,
        to_timestamp(m.start_time) at time zone 'UTC' as started_at_utc,
        m.duration as duration_seconds,
        m.patch as patch_id,
        m.leagueid as league_id,
        m.radiant_team_id as radiant_team_id,
        m.dire_team_id as dire_team_id,
        m.radiant_name as radiant_team_name,
        m.dire_name as dire_team_name,
        m.radiant_win as is_radiant_win,
        m.radiant_score as radiant_score,
        m.dire_score as dire_score,
        coalesce(length(m.objectives),0) > 0 as is_parsed,
        loaded_at_utc 
    from parsed

)

select * from matches