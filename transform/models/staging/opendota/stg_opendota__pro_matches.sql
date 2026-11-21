with source as( 

	select * from {{source('opendota', 'pro_matches') }}

),

match_rows as( 

    select
        loaded_at, 
        unnest(response::json[]) as pro_match
    from source

),

pro_matches as( 

	select
		(pro_match ->> 'match_id')::bigint as match_id,
		to_timestamp((pro_match ->> 'start_time')::bigint) at time zone 'UTC' as started_at_utc,
		(pro_match ->> 'duration')::bigint as duration_seconds,
		(pro_match ->> 'leagueid')::bigint as league_id,
		(pro_match ->> 'radiant_team_id')::bigint as radiant_team_id,
		(pro_match ->> 'dire_team_id')::bigint as dire_team_id,
		(pro_match ->> 'radiant_win')::bool as is_radiant_win,
        loaded_at as loaded_at_utc,
	from match_rows

),

dedup_pro_matches as ( 

	select 
		*
	from pro_matches 
	qualify row_number() over(partition by match_id order by loaded_at_utc desc) = 1

)

	select * from dedup_pro_matches