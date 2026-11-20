{{ config(materialized='table') }}

with base as (

    select * from {{ ref('base_opendota__match_details') }}

),

parsed as ( 
    
    select
        match_id,
        loaded_at_utc,
        json_transform(response, '{
            "players": [{
                "player_slot": "INTEGER",
                "item_0": "INTEGER",
                "item_1": "INTEGER",
                "item_2": "INTEGER",
                "item_3": "INTEGER",
                "item_4": "INTEGER",
                "item_5": "INTEGER",
                "backpack_0": "INTEGER",
                "backpack_1": "INTEGER",
                "backpack_2": "INTEGER",
                "item_neutral": "INTEGER",
                "item_neutral2": "INTEGER"  
            }]
        }') as pi
    from base

),

player_rows as ( 

    select
        match_id,
        loaded_at_utc,
        unnest(pi.players) as player
    from parsed

),

player_items as (

    select
        match_id,
        player.player_slot  as player_slot,
        player.item_0       as item_0,
        player.item_1       as item_1,
        player.item_2       as item_2,
        player.item_3       as item_3,
        player.item_4       as item_4,
        player.item_5       as item_5,
        player.backpack_0   as backpack_0,
        player.backpack_1   as backpack_1,
        player.backpack_2   as backpack_2,
        player.item_neutral as item_neutral,
        player.item_neutral2 as item_neutral_2,
        loaded_at_utc 
    from player_rows

),

final_items as ( 
    select
        match_id,
        player_slot,
        item_slot,
        item_id,
        loaded_at_utc
    from player_items
    unpivot( 
        item_id for item_slot in (
            item_0, item_1, item_2, item_3, item_4, item_5,
            backpack_0, backpack_1, backpack_2,
            item_neutral, item_neutral_2
        )
    )
    where item_id <> 0
)

select * from final_items