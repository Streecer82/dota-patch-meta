{{ config(materialized='table') }}

with base as (

    select * from {{ ref("base_opendota__match_details") }} 

),

parsed as ( 
    
    select
        match_id,
        loaded_at_utc,
        json_transform(response, '{
            "players": [{
                "player_slot": "INTEGER",
                "account_id": "BIGINT",
                "personaname": "VARCHAR",
                "name": "VARCHAR",
                "hero_id": "INTEGER",
                "isRadiant": "BOOLEAN",
                "kills": "INTEGER",
                "deaths": "INTEGER",
                "assists": "INTEGER",
                "last_hits": "INTEGER",
                "denies": "INTEGER",
                "gold_per_min": "INTEGER",
                "xp_per_min": "INTEGER",
                "net_worth": "INTEGER",
                "hero_damage": "INTEGER",
                "tower_damage": "INTEGER",
                "level": "INTEGER"    
            }]
        }') as p
    from base

),

player_rows as ( 
    select
        match_id,
        loaded_at_utc,
        unnest(p.players) as player
    from parsed
),

players as (

    select
        match_id,
        player.player_slot as player_slot,
        player.account_id as account_id,
        player.personaname as persona_name,
        player.name as player_name,
        player.hero_id as hero_id,
        player.isradiant as is_radiant,
        player.kills as kills,
        player.deaths as deaths,
        player.assists as assists,
        player.last_hits as last_hits,
        player.denies as denies,
        player.gold_per_min as gold_per_min,
        player.xp_per_min as xp_per_min,
        player.net_worth as net_worth,
        player.hero_damage as hero_damage,
        player.tower_damage as tower_damage,
        player.level as hero_level,
        loaded_at_utc 
    from player_rows

)

select * from players