with source as (

    select * from {{ source('opendota', 'heroes') }}

),

latest_load as (

    select response
    from source
    qualify loaded_at = max(loaded_at) over ()

),

heroes as (

    select
        (l.response -> k.hero_key ->> 'id')::integer as hero_id,
        l.response -> k.hero_key ->> 'name' as hero_internal_name,
        l.response -> k.hero_key ->> 'localized_name' as hero_name,
        l.response -> k.hero_key ->> 'primary_attr' as primary_attribute,
        l.response -> k.hero_key ->> 'attack_type' as attack_type
    from latest_load l,
        unnest(json_keys(l.response)) as k(hero_key)

)

select * from heroes