{{ config(materialized='table') }}

with base as (

select * from {{ ref('base_opendota__match_details') }}

),

parsed as (

SELECT 
	match_id,
	loaded_at_utc,
	json_transform(response, '{
		"objectives": [{ 
			"time": "INTEGER",
			"type": "VARCHAR",
			"key": "VARCHAR",
			"player_slot": "INTEGER"
		}]
	}') as o
from base

),

objective_rows as (

SELECT 
	match_id,
	loaded_at_utc,
	unnest(o.objectives) as objective,
	generate_subscripts(o.objectives,1) as objective_seq
from parsed

),

objectives as ( 

	select
		match_id,
		objective_seq as objective_seq,
		objective.time as event_at_seconds,
		objective.player_slot as player_slot,
		objective.key as objective_key,
		objective.type as objective_type,
		loaded_at_utc
	from objective_rows
	
)

select * from objectives