import streamlit as st

def render_nav():
    if "current_page" not in st.session_state:
        st.session_state.current_page = "chatbot"

    with st.sidebar:
        st.markdown("### Navigation")
        choice = st.radio(
            "Pages:",
            ["Chatbot", "Term Familiarity"],
            index=0 if st.session_state.current_page == "chatbot" else 1
        )

    st.session_state.current_page = (
        "chatbot" if choice == "Chatbot" else "terms"
    )