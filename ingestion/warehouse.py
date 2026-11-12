"""
Connecting to the DuckDB warehouse and saving raw API responses.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "dota.duckdb"
RAW_SCHEMA = "raw_opendota"


def get_connection():
    """Open the project database and make sure the raw schema exists."""
    # TODO: make sure the data folder exists (as in explore_api.py: .mkdir(parents=True, exist_ok=True))
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    # TODO: connect to DATABASE_PATH (duckdb wants the path as text: str(DATABASE_PATH))
    con = duckdb.connect(str(DATABASE_PATH))
    # TODO: create the RAW_SCHEMA schema if it doesn't exist
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {RAW_SCHEMA}")
    # TODO: return the connection
    return con

def create_raw_table(con, table_name):
    """Create raw_opendota.<table_name> with the standard raw columns, if it doesn't exist."""
    # TODO: CREATE TABLE IF NOT EXISTS with loaded_at TIMESTAMP, endpoint VARCHAR,
    #       request_params VARCHAR, response JSON
    #       (the table name can't be a ? placeholder, so build that part with an f-string)
    con.execute(f"""CREATE TABLE IF NOT EXISTS {RAW_SCHEMA}.{table_name}
                (
                    loaded_at TIMESTAMP,
                    endpoint VARCHAR,
                    request_params VARCHAR,
                    response json
                )
                """)


def save_response(con, table_name, endpoint, params, data):
    """Insert one API response into raw_opendota.<table_name>."""
    # TODO: an INSERT with four ? placeholders, and a list of four values:
    #       the current UTC time, the endpoint, params as JSON text, data as JSON text
    #       (params may be None: store it as an empty object, {}, rather than null)
    loaded_at = datetime.now(timezone.utc).replace(tzinfo=None)
    con.execute(
        f"""
        INSERT INTO {RAW_SCHEMA}.{table_name}
            (loaded_at, endpoint, request_params, response)
            values (?, ?, ?, ?)
        """,
        [loaded_at, endpoint, json.dumps(params or {}), json.dumps(data)],
        )


if __name__ == "__main__":
    con = get_connection()
    create_raw_table(con, "test_responses")
    save_response(con, "test_responses", "/test", {"a": 1}, [{"hero": "Axe"}])
    print(con.execute(f"select * from {RAW_SCHEMA}.test_responses").fetchall())
    con.execute(f"drop table {RAW_SCHEMA}.test_responses")