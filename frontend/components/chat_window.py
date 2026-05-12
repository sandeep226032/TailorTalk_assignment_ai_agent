import streamlit as st

def render_messages(messages: list):
    for msg in messages:
        avatar = "🧑" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

def render_input() -> str | None:
    return st.chat_input("Search your Drive...")