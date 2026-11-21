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
                "purchase_log": [{
                    "time":    "INTEGER",
                    "key":     "VARCHAR"
                }]
            }]
        }') as m
    from base

),

-- 1st unnest: one row per player, with that player's purchase list
player_rows as (

    select
        match_id,
        loaded_at_utc,
        unnest(m.players) as player
    from parsed

),

player_logs as (

    select
        match_id,
        loaded_at_utc,
        player.player_slot    as player_slot,
        player.purchase_log   as purchase_log
    from player_rows

),

-- 2nd unnest: one row per purchase, with its position in the log
purchase_rows as (

    select
        match_id,
        player_slot,
        loaded_at_utc,
        unnest(purchase_log)                   as purchase,
        generate_subscripts(purchase_log, 1)   as purchase_seq
    from player_logs

),

purchases as (

    select
        match_id,
        player_slot,
        purchase_seq,
        purchase.time      as purchased_at_seconds,
        purchase.key       as item_key,
        loaded_at_utc
    from purchase_rows

)

select * from purchases