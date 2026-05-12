import streamlit as st

def render_sidebar():
    with st.sidebar:
        st.header("💡 How to use")
        st.markdown("""
        **Search by name:** "Find files named budget"  
        **Search by type:** "Show me all PDFs"  
        **By content:** "Files containing invoice"  
        **By date:** "Files from last month"
        """)
        if st.button("🗑️ New Conversation", use_container_width=True):
            return "clear"  # Signal to app.py
    return None