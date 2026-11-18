with source as (

    select * from {{ source('opendota', 'items') }}

),

latest_load as (

    select response
    from source
    qualify loaded_at = max(loaded_at) over ()

),

items as (

    select
        (l.response -> k.item_key ->> 'id')::integer as item_id,
        k.item_key as item_key,
        l.response -> k.item_key ->> 'dname' as item_name,
        (l.response -> k.item_key ->> 'cost')::integer as item_cost
    from latest_load l,
        unnest(json_keys(l.response)) as k(item_key)

)

select * from items