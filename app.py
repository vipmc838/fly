import streamlit as st
import threading
from main import AgentApplication

def run_agent():
    agent = AgentApplication(config_path=None)
    agent.run()

if "agent_started" not in st.session_state:
    thread = threading.Thread(target=run_agent, daemon=True)
    thread.start()
    st.session_state.agent_started = True

st.set_page_config(page_title="Hello", layout="centered")
try:
    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    st.components.v1.html(html_content, height=800, scrolling=True)
except FileNotFoundError:
    st.write("Hello, World!")
