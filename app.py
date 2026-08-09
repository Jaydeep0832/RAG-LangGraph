"""
LangGraph RAG Demo — Interactive & User-Friendly Streamlit UI
Run: streamlit run app.py
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import json
from datetime import datetime
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent import MessagesState, agent

# ---------------------------------------------------------------------------
# Page Configuration & Styling
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="LangGraph RAG Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern UI styling
st.markdown(
    """
    <style>
    /* Header container styling */
    .header-card {
        background: linear-gradient(135deg, #1e1e2f 0%, #0d1117 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Interactive action buttons */
    div.stButton > button {
        border-radius: 8px;
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:hover {
        transform: translateY(-1px);
        border-color: #6366f1;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of (role, content, timestamp)

if "tool_traces" not in st.session_state:
    st.session_state.tool_traces = []  # list of trace dicts per turn

def set_quick_prompt(text: str):
    st.session_state.pending_prompt = text

pending_prompt = st.session_state.pop("pending_prompt", None)

# ---------------------------------------------------------------------------
# Header Section
# ---------------------------------------------------------------------------

st.markdown(
    """
<div class="header-card">
    <h1 style="margin: 0; font-size: 2.1rem; display: flex; align-items: center; gap: 10px;">
        🤖 LangGraph RAG & Reasoning Agent
    </h1>
    <p style="margin-top: 8px; margin-bottom: 0; color: #a0aec0; font-size: 1.02rem;">
        Stateful AI assistant powered by <b>LangGraph</b>, <b>Groq LLM</b>, <b>FAISS Vector Search</b>, and dynamic <b>Tool Execution</b>.
    </p>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar — Controls, Metrics, & Live Tool Trace
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("⚙️ Control Panel")

    # Clear chat action
    if st.button("🗑️ Clear Chat History", use_container_width=True, type="secondary"):
        st.session_state.chat_history = []
        st.session_state.tool_traces = []
        st.rerun()

    st.markdown("---")

    # Interactive Dashboard Metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Turns", len(st.session_state.chat_history) // 2)
    with col2:
        total_tools_called = sum(len(t) for t in st.session_state.tool_traces)
        st.metric("Tool Calls", total_tools_called)

    st.markdown("---")

    # Agent Tools Guide
    with st.expander("🛠️ Active Agent Tools", expanded=False):
        st.markdown(
            """
        - 📚 **`search_docs`**: FAISS semantic vector search over AI knowledge base.
        - ➕ **`add`**: Integer addition tool (`a + b`).
        - ✖️ **`multiply`**: Integer multiplication tool (`a * b`).
        - ➗ **`divide`**: Floating point division tool (`a / b`).
        """
        )

    st.markdown("---")

    # Live Tool Trace View
    st.subheader("🔍 Live Tool Trace")
    st.caption("Inspect real-time tool execution, inputs, and outputs per turn")

    if not st.session_state.tool_traces:
        st.info("No tool calls recorded yet. Try asking a question or running a calculation!")
    else:
        for i, trace in enumerate(reversed(st.session_state.tool_traces)):
            turn_num = len(st.session_state.tool_traces) - i
            turn_label = f"Turn {turn_num} ({len(trace)} call{'s' if len(trace)!=1 else ''})"

            with st.expander(turn_label, expanded=(i == 0)):
                if not trace:
                    st.caption("ℹ️ *No tools required — answered directly by LLM.*")
                else:
                    for idx, call in enumerate(trace):
                        tool_icon = "📚" if call["name"] == "search_docs" else "🧮"
                        st.markdown(f"{tool_icon} **Tool:** `{call['name']}`")

                        st.caption("📥 **Input Arguments:**")
                        st.code(json.dumps(call["args"], indent=2), language="json")

                        st.caption("📤 **Output Result:**")
                        st.code(str(call["result"]), language="text")

                        if idx < len(trace) - 1:
                            st.divider()

# ---------------------------------------------------------------------------
# Interactive Quick Suggestion Chips
# ---------------------------------------------------------------------------

if not st.session_state.chat_history:
    st.markdown("##### 💡 Try asking one of these quick sample questions:")
    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)

    with btn_col1:
        if st.button("📚 What are Embeddings?", use_container_width=True):
            set_quick_prompt("What are embeddings?")
            st.rerun()
    with btn_col2:
        if st.button("🔍 Explain FAISS Search", use_container_width=True):
            set_quick_prompt("Explain FAISS vector search and its key features")
            st.rerun()
    with btn_col3:
        if st.button("🧮 Calculate 125 * 45", use_container_width=True):
            set_quick_prompt("What is 125 * 45?")
            st.rerun()
    with btn_col4:
        if st.button("➗ Divide 1000 by 8", use_container_width=True):
            set_quick_prompt("What is 1000 / 8?")
            st.rerun()

st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Chat History Display
# ---------------------------------------------------------------------------

for item in st.session_state.chat_history:
    role = item[0]
    content = item[1]
    time_str = item[2] if len(item) > 2 else ""

    with st.chat_message(role):
        st.markdown(content)
        if time_str:
            st.caption(f"<span style='font-size: 0.75rem; color: #718096;'>{time_str}</span>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Chat Input & Processing
# ---------------------------------------------------------------------------

user_input = st.chat_input("Ask a question, search docs, or perform a calculation...")

# Override input if a quick button was clicked
prompt = pending_prompt if pending_prompt else user_input

if prompt:
    now_time = datetime.now().strftime("%H:%M:%S")

    # Save & display user message immediately
    st.session_state.chat_history.append(("user", prompt, now_time))
    with st.chat_message("user"):
        st.markdown(prompt)
        st.caption(f"<span style='font-size: 0.75rem; color: #718096;'>{now_time}</span>", unsafe_allow_html=True)

    # Run agent & display response
    with st.chat_message("assistant"):
        status_holder = st.empty()
        with status_holder.container():
            with st.spinner("🤖 Agent reasoning & evaluating tools..."):
                initial_state: MessagesState = {
                    "messages": [HumanMessage(content=prompt)],
                    "llm_calls": 0,
                }
                result = agent.invoke(initial_state)

        status_holder.empty()

        # Parse tool calls and results from message history
        trace = []
        messages = result["messages"]

        pending_calls: dict[str, dict] = {}
        for msg in messages:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    pending_calls[tc["id"]] = {
                        "name": tc["name"],
                        "args": tc["args"],
                        "result": "",
                    }
            elif isinstance(msg, ToolMessage):
                if msg.tool_call_id in pending_calls:
                    pending_calls[msg.tool_call_id]["result"] = msg.content

        trace = list(pending_calls.values())
        st.session_state.tool_traces.append(trace)

        # Notify via toast if tools were called
        if trace:
            tools_used_str = ", ".join([f"`{t['name']}`" for t in trace])
            st.toast(f"⚡ Tools executed: {tools_used_str}", icon="🛠️")

        # Find final assistant answer
        final_answer = ""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                final_answer = msg.content
                break

        if not final_answer:
            final_answer = "I've processed your request."

        st.markdown(final_answer)
        resp_time = datetime.now().strftime("%H:%M:%S")
        st.caption(f"<span style='font-size: 0.75rem; color: #718096;'>{resp_time}</span>", unsafe_allow_html=True)
        st.session_state.chat_history.append(("assistant", final_answer, resp_time))

    # Rerun to refresh sidebar trace and metrics
    st.rerun()