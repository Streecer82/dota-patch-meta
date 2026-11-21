{{ config(materialized='table') }}

with source as (

    select * from {{ source('opendota', 'match_details') }}

),

with_match_id as (

    select
        (response ->> 'match_id')::bigint as match_id,
        loaded_at as loaded_at_utc,
        response
    from source

),

latest_per_match as (

    select
        * 
    from with_match_id
    qualify row_number() over (partition by match_id order by loaded_at_utc desc) = 1

)

select * from latest_per_match