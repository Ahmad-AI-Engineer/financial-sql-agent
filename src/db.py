import psycopg
from psycopg.rows import dict_row
from src.config import DB_CONNECT_TIMEOUT, DB_DSN


def get_connection():
    """Open a new PostgreSQL connection.

    row_factory=dict_row means each row comes back as a dictionary
    like {"column_name": value}, which is easy to turn into JSON later.
    """
    return psycopg.connect(
        DB_DSN,
        row_factory=dict_row,
        connect_timeout=DB_CONNECT_TIMEOUT,
    )


def run_select(query: str):
    """Run a SELECT query and return the rows as a list of dictionaries.

    Raises an exception if the SQL is invalid — the agent's tool will
    catch that and decide whether to retry.
    """
    with get_connection() as conn:
        # Postgres itself refuses any write in a read-only transaction, so this
        # holds even if a write slips past the keyword check in tools.py.
        conn.read_only = True
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()
