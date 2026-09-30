import json
import re
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from src.db import run_select
from src.config import MAX_RETRIES

# Counts consecutive SQL failures for each conversation thread.
# Example: {"session-1": 2}
_failure_counts: dict[str, int] = {}


def _thread_id_from(config: RunnableConfig) -> str:
    """Pull the current conversation's thread_id out of the runtime config."""
    try:
        return config["configurable"]["thread_id"]
    except (KeyError, TypeError):
        return "default"


_BANNED_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|vacuum)\b",
    re.IGNORECASE,
)


def _is_select_only(query: str) -> bool:
    """Allow only read-only SELECT queries. Blocks INSERT/UPDATE/DELETE/DROP etc.

    This keeps the agent safe: it can read the financial data but never change it.
    """
    q = query.strip().rstrip(";")
    # A second statement is how a write sneaks in behind a harmless SELECT.
    if ";" in q:
        return False
    if not re.match(r"\s*(select|with)\b", q, re.IGNORECASE):
        return False
    # Word boundaries, not spaces: a newline or tab before the keyword must count too.
    return not _BANNED_KEYWORDS.search(q)


@tool
def run_sql(query: str, config: RunnableConfig) -> str:
    """Run a read-only PostgreSQL SELECT query against the financial database
    and return the resulting rows.

    Args:
        query: A single valid PostgreSQL SELECT statement.

    Returns:
        The rows as a JSON string on success, or an error/instruction message
        on failure.
    """
    thread_id = _thread_id_from(config)

    # ---- Safety check: only SELECT is allowed ----
    if not _is_select_only(query):
        return ("ERROR: Only read-only SELECT queries are allowed. "
                "Please write a SELECT statement.")

    # ---- Try to execute the query ----
    try:
        rows = run_select(query)
        _failure_counts[thread_id] = 0  # success -> reset the retry counter
        # default=str so dates / Decimals serialize cleanly to JSON
        return json.dumps({"row_count": len(rows), "rows": rows}, default=str)

    except Exception as e:
        # Count this failure for the current conversation.
        _failure_counts[thread_id] = _failure_counts.get(thread_id, 0) + 1
        attempts = _failure_counts[thread_id]

        if attempts >= MAX_RETRIES:
            # Give up: reset so the next question starts clean, and tell the
            # LLM to stop trying and apologise to the user.
            _failure_counts[thread_id] = 0
            return (
                "MAX_RETRIES_EXCEEDED: The query failed "
                f"{MAX_RETRIES} times. Do NOT call run_sql again. "
                "Reply to the user with a short, polite apology explaining "
                "that you could not retrieve the data right now."
            )

        # Still have retries left: hand the error back so the LLM can fix the SQL.
        return (
            f"SQL_ERROR (attempt {attempts} of {MAX_RETRIES}): {e}\n"
            "Fix the SQL query and call run_sql again."
        )


# The list the agent will be given.
TOOLS = [run_sql]
