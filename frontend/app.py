import streamlit as st
import uuid
import os
from components.sidebar import render_sidebar
from components.chat_window import render_messages, render_input
from services.api_client import APIClient

# Init
client = APIClient(base_url=os.getenv("BACKEND_URL", "http://localhost:8000/api/v1"))

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render
st.title("🗂️ TailorTalk Drive Agent")

action = render_sidebar()
if action == "clear":
    client.clear_session(st.session_state.session_id)
    st.session_state.messages = []
    st.rerun()

render_messages(st.session_state.messages)

if prompt := render_input():
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.spinner("Searching..."):
        reply = client.send_message(st.session_state.session_id, prompt)
    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()