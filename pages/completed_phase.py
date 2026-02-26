import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timezone

st.set_page_config(layout="wide")
st.markdown(
    """
    <style>
        [data-testid="stSidebarNav"] {display: none;}
    </style>
    """,
    unsafe_allow_html=True
)

PROLIFIC_LINK = "https://app.prolific.com/submissions/complete?cc=CZFT8YSF"

# ---------------------------
# FLOW GUARD
# ---------------------------
if "prolific_id" not in st.session_state or "last_batch" not in st.session_state:
    st.error("This page can only be accessed after completing the study.")
    st.stop()

prolific_id = st.session_state.prolific_id
batch_id = st.session_state.last_batch


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

if st.button("Submit answer"):
    if choice is None:
        st.error("Please make a selection to continue.")
        st.stop()

    client = MongoClient(st.secrets["MONGO_URI"])
    db = client["pls"]
    users_collection = db["users"]

    users_collection.update_one(
        {"prolific_id": prolific_id},
        {"$set": {
            f"phases.static.batches.{batch_id}.confirmed_completion": choice.startswith("Yes"),
            "timestamp": datetime.now(timezone.utc)
        }}
    )

    st.success("Your response has been recorded.")

    st.link_button(
        "Go back to Prolific",
        PROLIFIC_LINK
    )
    st.stop()