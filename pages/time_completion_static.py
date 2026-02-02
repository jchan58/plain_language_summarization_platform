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

st.title("Time Recording and Feedback for Phase")

st.markdown("""
Please enter the following in **seconds**:

1. Time to complete this **phase**
2. Time to complete the **Select All That Apply (SATA)** questions  
3. Any optional feedback about this phase
""")

batch_time = st.text_input("Please enter the total time it took to complete this phase (in seconds)")
sata_time = st.text_input("Please enter the total time it took to answer the **Select All That Apply (SATA)** questions (in seconds)")
feedback = st.text_area("Please enter any suggestions or comments you have for this static phase (optional)")

def is_number(x):
    try:
        float(x)
        return True
    except:
        return False

valid = is_number(batch_time) and is_number(sata_time)

if st.button("Submit"):
    if not batch_time or not sata_time:
        st.error("Please fill in both time fields before continuing.")
        st.stop()
    if not valid:
        st.error("Please enter numbers only for the time fields.")
        st.stop()

    prolific_id = st.session_state.get("prolific_id")
    batch_id = st.session_state.get("last_batch")
    full_type = st.session_state.get("last_full_type")

    client = MongoClient(st.secrets["MONGO_URI"])
    db = client["pls"]
    users_collection = db["users"]

    users_collection.update_one(
        {"prolific_id": prolific_id},
        {"$set": {
            f"phases.static.batches.{batch_id}.time_completion": {
                "batch_time_seconds": float(batch_time),
                "sata_time_seconds": float(sata_time),
                "feedback": feedback,
                "timestamp": datetime.utcnow()
            }
        }}
    )

    st.success("Saved! Moving to next phase…")
    st.switch_page("app.py")