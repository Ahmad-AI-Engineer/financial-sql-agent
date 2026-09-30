"""Streamlit interface for the financial SQL agent.

Run from the project root with:

    python -m streamlit run app.py
"""

import uuid

import streamlit as st

from src.agent import ask, build_agent


PAGE_TITLE = "Financial SQL Agent"
EXAMPLE_QUESTIONS = (
    "How many customers do we have?",
    "What is the total amount of unpaid invoices?",
    "Show the top 5 customers by total invoice amount.",
    "How much did we spend on salaries last year?",
)

st.set_page_config(page_title=PAGE_TITLE, page_icon="💰")


@st.cache_resource(show_spinner="Starting the agent...")
def get_agent():
    """Build one agent so its in-memory checkpointer survives UI reruns."""
    return build_agent()


def initialize_session() -> None:
    """Create the state used by one browser conversation."""
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = f"streamlit-{uuid.uuid4()}"
    if "history" not in st.session_state:
        st.session_state.history = []


def render_sidebar() -> None:
    """Render the application summary and conversation controls."""
    with st.sidebar:
        st.header(f"💰 {PAGE_TITLE}")
        st.caption(
            "Ask questions in plain English. The agent writes SQL, queries "
            "PostgreSQL, and explains the result."
        )
        st.divider()
        st.write("**Example questions**")
        for question in EXAMPLE_QUESTIONS:
            st.write(f"- {question}")
        st.divider()
        if st.button("🧹 Clear conversation"):
            st.session_state.thread_id = f"streamlit-{uuid.uuid4()}"
            st.session_state.history = []
            st.rerun()


def render_history() -> None:
    """Display messages already sent in this browser session."""
    for message in st.session_state.history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def handle_question(agent) -> None:
    """Send the latest user question to the agent and display its answer."""
    question = st.chat_input("Ask about your financial data...")
    if not question:
        return

    st.session_state.history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking (writing SQL, querying the database)..."):
            try:
                answer = ask(
                    agent,
                    question,
                    thread_id=st.session_state.thread_id,
                )
            except Exception as error:
                answer = f"Sorry, something went wrong: {error}"
        st.markdown(answer)

    st.session_state.history.append({"role": "assistant", "content": answer})


def main() -> None:
    initialize_session()
    render_sidebar()
    render_history()
    handle_question(get_agent())


if __name__ == "__main__":
    main()
