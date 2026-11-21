with source as (

    select * from {{ source('opendota', 'leagues') }}

),

latest_load as (

    select response
    from source
    qualify loaded_at = max(loaded_at) over ()

),

league_rows as (

    select unnest(response::json[]) as league
    from latest_load

),

leagues as (

    select
        (league ->> 'leagueid')::bigint   as league_id,
        league ->> 'name'                 as league_name,
        league ->> 'tier'                 as league_tier
    from league_rows

)

select * from leagues