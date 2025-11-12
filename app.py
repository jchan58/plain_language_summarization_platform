import streamlit as st
from pymongo import MongoClient
import datetime
import pandas as pd
from openai import OpenAI
from pages.chatbot import run_chatbot

st.set_page_config(layout="wide")

@st.cache_resource
def get_mongo_client():
    return MongoClient(st.secrets["MONGO_URI"])

# connect to MongoDB
MONGO_URI = st.secrets["MONGO_URI"]
client = MongoClient(MONGO_URI)
db = client["pls"]
users_collection = db["users"]

# load approved IDs 
approved_ids = pd.read_csv("approved_ids.csv")["prolific_id"].tolist()
user_df = pd.read_csv("example_user.csv")

if not st.session_state.get("logged_in", False):
    st.title("Making Research Articles Easier to Read – Pilot Study")
    st.markdown("""
    By entering your Mturk ID you agree to our [Terms and Conditions](https://docs.google.com/document/d/1wfvGWg69Vg3xroLDxpJXwe1_KWY72w0Z4ut59hA5iTM/edit?usp=sharing).
    """, unsafe_allow_html=True)

    prolific_id = st.text_input("Please enter your Mturk ID to begin annotating").strip()
    if st.button("Enter"):
        if not prolific_id:
            st.error("Please enter your Mturk ID.")
            st.stop()

        if prolific_id.lower() not in [str(id).lower() for id in approved_ids]:
            st.error("Sorry, your Mturk ID is not approved for this study.")
            st.stop()

        # --- Fetch or create user record ---
        user = users_collection.find_one({"prolific_id": prolific_id})
        if not user:
            user_rows = user_df[user_df["user_id"] == int(prolific_id)]

            phases = {
                "static": {"abstracts": {}, "completed": False},
                "interactive": {"abstracts": {}, "completed": False},
                "finetuned": {"abstracts": {}, "completed": False},
            }

            # loop over each row assigned to this user
            for _, row in user_rows.iterrows():
                phase_type = row["type"]  # 'static', 'interactive', or 'finetuned'
                abstract_key = str(row["abstract_id"])
                phases[phase_type]["abstracts"][abstract_key] = {
                    "abstract_title": row["abstract_title"],
                    "abstract": row["abstract"],
                    "short_answers": {
                        "main_idea": "", 
                        "methods": "", 
                        "results": ""
                    }, 
                    "completed": False
                }

            users_collection.insert_one({
                "prolific_id": prolific_id,
                "created_at": datetime.datetime.utcnow(),
                "accepted_terms": True,
                "phases": phases
            })
            user = users_collection.find_one({"prolific_id": prolific_id})  # reload fresh doc ✅

        # restore progress index if available
        start_index = (
            user.get("phases", {})
                .get("interactive", {})
                .get("last_completed_index", 0)
        )
        st.session_state.abstract_index = start_index

        # save login state
        st.session_state.logged_in = True
        st.session_state.prolific_id = prolific_id
        st.rerun()

else:
    # no header here
    run_chatbot(st.session_state.prolific_id)
