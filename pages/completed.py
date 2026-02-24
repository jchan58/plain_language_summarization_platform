import streamlit as st
from pymongo import MongoClient
from datetime import datetime
from navigation import render_nav



@st.cache_resource
def get_mongo_client():
    return MongoClient(st.secrets["MONGO_URI"])

# connect to MongoDB
MONGO_URI = st.secrets["MONGO_URI"]
client = MongoClient(MONGO_URI)
db = client["pls"]
users_collection = db["users"]

@st.dialog("Are you sure you want to log out?", dismissible=False)
def logout_confirm_dialog(prolific_id):
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Stay on page"):
            st.session_state.show_logout_dialog = False
            st.rerun()

    with col2:
        if st.button("Logout"):
            st.session_state.show_logout_dialog = False
            users_collection.update_one(
                {"prolific_id": prolific_id},
                {"$set": {
                    "phases.interactive.last_completed_index":
                        st.session_state.get("abstract_index", 0)
                }},
                upsert=True
            )

            st.session_state.logged_in = False
            st.session_state.prolific_id = None
            st.switch_page("app.py")


st.header("You have completed all the tasks for this batch and can exit this page!")
if st.button("Go back to login page"):
    st.switch_page("app.py")