with source as ( 

    select *from {{ source('opendota', 'match_sample') }}

),

renamed as (

    select
        match_id,
        patch_id,
        patch_name,
        match_started_utc as started_at_utc,
        sample_seed,
        sampled_at as sampled_at_utc
    from source

)

select * from renamed