import yaml
from src.db import get_connection
from src.config import SCHEMA_PATH

# Query 1: every column of every table in the public schema.
COLUMNS_SQL = """
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;
"""

# Query 2: foreign keys, so the model knows how tables join together.
FKS_SQL = """
SELECT
    tc.table_name      AS from_table,
    kcu.column_name    AS from_column,
    ccu.table_name     AS to_table,
    ccu.column_name    AS to_column
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
   AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
    ON ccu.constraint_name = tc.constraint_name
   AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public';
"""


def extract():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(COLUMNS_SQL)
            columns = cur.fetchall()
            cur.execute(FKS_SQL)
            fks = cur.fetchall()

    # Build a clean dictionary: {table_name: {columns: [...], foreign_keys: [...]}}
    schema: dict = {}
    for row in columns:
        table = row["table_name"]
        schema.setdefault(table, {"columns": [], "foreign_keys": []})
        schema[table]["columns"].append(
            {
                "name": row["column_name"],
                "type": row["data_type"],
                "nullable": row["is_nullable"] == "YES",
            }
        )

    for fk in fks:
        table = fk["from_table"]
        schema.setdefault(table, {"columns": [], "foreign_keys": []})
        schema[table]["foreign_keys"].append(
            f'{fk["from_column"]} -> {fk["to_table"]}.{fk["to_column"]}'
        )

    # Write it out as YAML.
    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SCHEMA_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"tables": schema}, f, sort_keys=True, default_flow_style=False)

    print(f"Schema written to {SCHEMA_PATH}")
    print(f"Found {len(schema)} tables: {', '.join(schema.keys())}")


def load_schema_text() -> str:
    """Read schema.yaml back as plain text (used inside the system prompt)."""
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    extract()
