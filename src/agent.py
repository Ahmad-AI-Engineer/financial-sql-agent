from langchain.agents import create_agent
from langchain_openrouter import ChatOpenRouter
from langgraph.checkpoint.memory import InMemorySaver
from src.config import OPENROUTER_API_KEY, OPENROUTER_MODEL
from src.tools import TOOLS
from src.extract_schema import load_schema_text


def build_system_prompt() -> str:
    """The instructions given to the LLM on every turn.

    We inject the database schema (from schema.yaml) so the model knows exactly
    which tables and columns exist when it writes SQL.
    """
    schema_text = load_schema_text()
    return f"""You are a helpful financial data assistant.

You answer questions about a PostgreSQL financial database by writing SQL.

DATABASE SCHEMA (tables, columns, and how they join):
{schema_text}

RULES:
1. To get data, call the `run_sql` tool with ONE valid PostgreSQL SELECT query.
2. Only SELECT queries are allowed. Never try to modify data.
3. When `run_sql` returns rows, explain the answer to the user in simple,
   clear, human-readable language. Summarise numbers nicely (e.g. currency,
   totals, top items). Do NOT show raw JSON to the user.
4. If `run_sql` returns a message starting with "SQL_ERROR", read the error,
   fix your SQL, and call `run_sql` again.
5. If `run_sql` returns a message starting with "MAX_RETRIES_EXCEEDED", stop.
   Do not call the tool again. Give the user a short, polite apology.
6. Use the earlier conversation (your memory) to understand follow-up
   questions like "what about last month?" or "show only the top 5".
"""


def build_llm() -> ChatOpenRouter:
    """Create the OpenRouter chat model.

    The model must support tool calling (function calling) for the agent to work.
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Add it to .env or the server environment."
        )

    return ChatOpenRouter(
        model=OPENROUTER_MODEL,
        api_key=OPENROUTER_API_KEY,
        temperature=0.1,  # low = more predictable SQL
    )


def build_agent():
    """Create and return the compiled agent.

    The InMemorySaver checkpointer gives the agent short-term memory: pass the
    same thread_id across calls to continue a conversation.
    """
    llm = build_llm()
    checkpointer = InMemorySaver()  # short-term memory backend

    agent = create_agent(
        model=llm,
        tools=TOOLS,
        system_prompt=build_system_prompt(),
        checkpointer=checkpointer,
    )
    return agent


def ask(agent, question: str, thread_id: str = "session-1") -> str:
    """Send one question to the agent and return its final text answer.

    thread_id ties messages together into one conversation (short-term memory).
    Reuse the same thread_id to let the agent remember previous turns.
    """
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        {"configurable": {"thread_id": thread_id}},
    )
    return result["messages"][-1].content


# Quick manual test (no UI):  python -m src.agent
if __name__ == "__main__":
    a = build_agent()
    print(ask(a, "How many customers do we have?"))
    print(ask(a, "And how many of them are from the USA?"))  # tests memory
