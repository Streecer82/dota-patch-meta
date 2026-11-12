"""
Load reference data (heroes, patches, items) from OpenDota into the raw schema.

Run from the project root:
    python ingestion/load_reference.py
"""

from api import get_json
from warehouse import get_connection, create_raw_table, save_response

# (table name, endpoint) for each reference dataset
REFERENCE_ENDPOINTS = [
    ("heroes", "/constants/heroes"),
    ("patches", "/constants/patch"),
    ("items", "/constants/items"),
]


def load_reference():
    """Fetch each reference endpoint and save the response to its raw table."""
    con = get_connection()

    for table_name, endpoint in REFERENCE_ENDPOINTS:
        create_raw_table(con, table_name)
        data = get_json(endpoint)
        save_response(con, table_name, endpoint, None, data)
        print(f"{table_name}: saved {len(data)} records from {endpoint}")

    con.close()


if __name__ == "__main__":
    load_reference()