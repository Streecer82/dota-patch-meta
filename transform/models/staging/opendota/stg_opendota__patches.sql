with source as (

    select * from {{ source('opendota', 'patches') }}

),

latest_load as (

    select response
    from source
    qualify loaded_at = max(loaded_at) over ()

),

patch_rows as (

    select unnest(response::json[]) as patch
    from latest_load
),

patches as (

    select 
      (patch ->> 'id')::integer as patch_id,
      patch ->> 'name' as patch_name,
      (patch ->> 'date')::timestamptz at time zone 'UTC' as released_at_utc
    from patch_rows

)

select * from patches