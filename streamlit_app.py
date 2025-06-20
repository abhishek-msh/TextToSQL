import os
import re
import json
import uuid
import requests
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timezone
from typing import Generator, List
import sqlparse
import pandas as pd

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
DEFAULT_API_URL = os.getenv("API_URL", "http://127.0.0.1:8083")


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------


def generate_ids() -> tuple[str, str]:
    """Generate a session and conversation UUID pair."""
    return str(uuid.uuid4()), str(uuid.uuid4())


def _beautify(text: str) -> str:
    """Prettify raw status/log strings for display purposes."""
    if not text:
        return ""
    text = text.replace("_", " ")
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return re.sub(r"\s+", " ", text).strip().capitalize()


# -----------------------------------------------------------------------------
# Streaming parser
# -----------------------------------------------------------------------------


def stream_answer(api_url: str, payload: dict) -> Generator[str, None, None]:
    """Yield Server‑Sent‑Events chunks returned by the backend."""
    try:
        response = requests.post(
            f"{api_url}/get_answer_streaming",
            json=payload,
            stream=True,
            headers={"Accept": "text/event-stream"},
            timeout=120,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        # Surface transport errors to the chat UI
        yield f"ERROR: {exc}"
        return

    for raw in response.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data:"):
            continue
        data = raw[5:].strip()
        if data in ("[START]", "[DONE]", ""):
            continue
        yield data


# -----------------------------------------------------------------------------
# Rendering helpers
# -----------------------------------------------------------------------------


def _render_sql(sql: str):
    st.markdown("**SQL Query:**")
    st.code(sqlparse.format(sql, reindent=True), language="sql")


def _render_markdown(md: str):
    st.markdown(md)


def _render_dataframe(df):
    st.markdown("**SQL Query Result:**")
    if isinstance(df, str):
        df = json.loads(df)
    df = pd.DataFrame(df)
    st.dataframe(df)


def _render_plotly_graph(fig_json: dict):
    json_str = json.dumps(fig_json).replace("'", "&#x27;")
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.plot.ly/plotly-2.28.0.min.js"></script>
    </head>
    <body>
        <div id=\"myDiv\"></div>
        <script>
            var jsonData = JSON.parse('{json_str}');
            Plotly.newPlot('myDiv', jsonData.data, jsonData.layout);
        </script>
    </body>
    </html>"""
    components.html(html, height=450, scrolling=False)


def _maybe_plotly_dict(d: dict) -> bool:
    return isinstance(d, dict) and "data" in d and "layout" in d


# -----------------------------------------------------------------------------
# Chunk renderer
# -----------------------------------------------------------------------------


def render_chunk(chunk: str):
    """Render one SSE chunk and return a status tag for further handling."""

    # ------------------------------------------------------------------
    # LOG chunks are now rendered by the status bar in the main loop.
    # Simply return a tag so the caller can skip normal rendering.
    # ------------------------------------------------------------------
    if chunk.startswith("[LOGS]"):
        return "log"

    # Attempt to parse structured JSON responses
    try:
        parsed = json.loads(chunk)
        if isinstance(parsed, dict):
            # Structured BI‑Assistant response ----------------------------------
            if "botResponse" in parsed and parsed["botResponse"]:
                last = parsed["botResponse"][-1]
                if "graphFigureJson" in last and last["graphFigureJson"]:
                    try:
                        fig_dict = json.loads(last["graphFigureJson"])
                        if _maybe_plotly_dict(fig_dict):
                            _render_plotly_graph(fig_dict)
                            return "graph"
                    except json.JSONDecodeError:
                        pass
            elif parsed.get("type") in {"answer", "userTextRephrased"}:
                if parsed.get("type") == "answer":
                    st.markdown("**Answer:**")
                elif parsed.get("type") == "userTextRephrased":
                    st.markdown("**Rephrased Question:**")
                _render_markdown(parsed.get("content", ""))
                return "text"
            elif parsed.get("type") == "sqlQuery":
                _render_sql(parsed.get("content", ""))
                return "sql"
            elif parsed.get("type") == "sqlError":
                st.error(f"SQL Error: {parsed.get('content', 'Unknown error')}")
                return "error"
            elif parsed.get("type") == "sqlQueryResponse":
                _render_dataframe(parsed["content"])
                return "dataframe"
        # # Fallback: show raw JSON for debugging
        # st.json(parsed, expanded=False)
        return "json"
    except json.JSONDecodeError:
        pass

    # Plain text fallback
    st.markdown(chunk)
    return "text"


# -----------------------------------------------------------------------------
# Streamlit UI
# -----------------------------------------------------------------------------


def main():
    st.set_page_config(page_title="BI Assistant", page_icon="🤖", layout="wide")
    st.title("🤖 BI Assistant – Interactive Chat")

    # --------------------------------------------------------------
    # Sidebar configuration
    # --------------------------------------------------------------
    st.sidebar.header("🔧 Settings & Credentials")
    api_url = st.sidebar.text_input("API Base URL", value=DEFAULT_API_URL)
    email = st.sidebar.text_input("Email", value="abhishek@test.com")
    client_name = st.sidebar.text_input("Client Name", value="AI-nlToSql")
    tenant_id = st.sidebar.text_input(
        "Tenant ID", value="23445e8b-74a4-4b8e-b88a-a13ba5721a58"
    )
    user_id = st.sidebar.text_input("User ID", value="abhishek")

    # --------------------------------------------------------------
    # Session‑level state initialisation
    # --------------------------------------------------------------
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id, st.session_state.conversation_id = generate_ids()

    # --------------------------------------------------------------
    # Chat history replay
    # --------------------------------------------------------------
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if isinstance(msg["content"], list):
                for ch in msg["content"]:
                    render_chunk(ch)
            else:
                st.markdown(msg["content"])

    # --------------------------------------------------------------
    # New user prompt
    # --------------------------------------------------------------
    prompt = st.chat_input("Ask your BI question…")
    if prompt:
        # Store user message in state for persistence
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Immediately render the user bubble
        with st.chat_message("user"):
            st.markdown(prompt)

        # Build the backend request payload
        date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        payload = {
            "emailID": email,
            "clientName": client_name,
            "tenantId": tenant_id,
            "userID": user_id,
            "sessionID": st.session_state.session_id,
            "conversationID": st.session_state.conversation_id,
            "userText": prompt,
            "date": date,
        }

        # ----------------------------------------------------------
        # Assistant response bubble with live status updates
        # ----------------------------------------------------------
        assistant_chunks: List[str] = []
        with st.chat_message("assistant"):
            # The new status bar keeps the user informed while the backend streams
            # events. As soon as the first chunk arrives, the label flips to the
            # latest log message.
            with st.status("Processing…", expanded=True) as status_bar:
                container = st.container()
                for chunk in stream_answer(api_url, payload):
                    assistant_chunks.append(chunk)

                    # Handle log chunks by updating the status bar in‑place
                    if chunk.startswith("[LOGS]"):
                        log_msg = _beautify(chunk.split("-", 1)[-1])
                        status_bar.update(label=log_msg, state="running")
                        continue  # Do not render log chunks in the transcript

                    # Render all other chunk types normally
                    with container:
                        render_chunk(chunk)

                # Finalise the status bar once the stream is done
                status_bar.update(label="Completed ✅", state="complete")

        # Append assistant chunks to history and rerun so the UI collapses the
        # spinner/status component for previous exchanges.
        st.session_state.messages.append(
            {"role": "assistant", "content": assistant_chunks}
        )
        st.rerun()


# -----------------------------------------------------------------------------
# Streamlit helper – detect if running under `streamlit run`
# -----------------------------------------------------------------------------


def _running_with_streamlit() -> bool:
    try:
        return st.runtime.exists()
    except Exception:
        return getattr(st, "_is_running_with_streamlit", False)


# -----------------------------------------------------------------------------
if __name__ == "__main__":
    if _running_with_streamlit():
        main()
    else:
        print("Use: streamlit run streamlit_app.py")
