{{ config(materialized='table') }}

with base as (

    select * from {{ ref("base_opendota__match_details") }} 

),

parsed as ( 
    
    select
        match_id,
        loaded_at_utc,
        json_transform(response, '{
            "picks_bans": [{
                "order": "INTEGER",
                "is_pick": "BOOLEAN",
                "hero_id": "INTEGER",
                "team": "INTEGER"   
            }]
        }') as pb
    from base

),

picks_bans_rows as ( 
    select
        match_id,
        loaded_at_utc,
        unnest(pb.picks_bans) as pick_ban
    from parsed
),

picks_bans as (

    select
        match_id,
        pick_ban."order" as pick_ban_order,
        pick_ban.is_pick as is_pick,
        pick_ban.hero_id as hero_id,
        pick_ban.team as team_number,
        case 
            when pick_ban.team = 0 then 'radiant'
            when pick_ban.team = 1 then 'dire'
        end as side,
        loaded_at_utc 
    from picks_bans_rows

)

select * from picks_bans