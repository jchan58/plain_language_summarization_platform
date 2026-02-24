import streamlit as st
from pymongo import MongoClient
from datetime import datetime

st.set_page_config(layout="wide")
st.markdown(
    """
    <style>
        [data-testid="stSidebarNav"] {display: none;}
    </style>
    """,
    unsafe_allow_html=True
)

PROLIFIC_LINK = "https://app.prolific.com/"

st.title("Study Completion")

st.markdown("""
Thank you for completing this study.

Please choose yes or no if you would like to participate in the next stage of this study.
""")

choice = st.radio(
    "Please select one option:",
    [
        "Yes, I would like to participate in the next stage of this study",
        "No, I would not like to participate in the next stage of this study"
    ],
    index=None
)

if st.button("Continue"):
    if choice is None:
        st.error("Please make a selection to continue.")
        st.stop()

    prolific_id = st.session_state.get("prolific_id")
    batch_id = st.session_state.get("last_batch")

    client = MongoClient(st.secrets["MONGO_URI"])
    db = client["pls"]
    users_collection = db["users"]

    users_collection.update_one(
        {"prolific_id": prolific_id},
        {"$set": {
            f"phases.static.batches.{batch_id}.confirmed_completion": choice.startswith("Yes"),
            "timestamp": datetime.utcnow()
        }}
    )

    # Immediate redirect to Prolific
    st.markdown(
        f"""
        <meta http-equiv="refresh" content="0; url={PROLIFIC_LINK}">
        """,
        unsafe_allow_html=True
    )