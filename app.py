import streamlit as st
from pymongo import MongoClient
import datetime
import pandas as pd
from openai import OpenAI
from pages.chatbot import run_chatbot
from pages.term_familarity_page import run_terms
import ast

# hide the sidebar
st.markdown(
    """
    <style>
        [data-testid="stSidebarNav"] {display: none;}
    </style>
    """,
    unsafe_allow_html=True
)
# set the page to wide mode

st.set_page_config(layout="wide")

# connect to mongodb
@st.cache_resource
def get_mongo_client():
    return MongoClient(st.secrets["MONGO_URI"])
MONGO_URI = st.secrets["MONGO_URI"]
client = MongoClient(MONGO_URI)
db = client["pls"]
users_collection = db["users"]
abstract_collection = db['abstracts']

# load approved IDs and dataframe for all the abstracts etc., 
approved_ids = pd.read_csv("approved_ids.csv")["prolific_id"].tolist()
user_df = pd.read_csv("final_user_batches.csv")

# check if the user exists in db if they don't 
if not st.session_state.get("logged_in", False):
    st.title("Making Research Articles Easier to Read – Pilot Study")
    st.markdown("""
    By entering your Mturk ID you agree to our [Terms and Conditions](https://docs.google.com/document/d/1HBwhqiquyXuu47wyncbAKvA4y8TbcXaK7n-Jv8t0FPs/edit?usp=sharing).
    """, unsafe_allow_html=True)

    prolific_id = st.text_input("Please enter your Mturk ID to begin annotating").strip()
    if st.button("Enter"):
        if not prolific_id:
            st.error("Please enter your Mturk ID.")
            st.stop()

        if prolific_id.lower() not in [str(id).lower() for id in approved_ids]:
            st.error("Sorry, your Mturk ID is not approved for this study.")
            st.stop()

        # check if user exists if it doesn't exist create using user_df
        user = users_collection.find_one({"prolific_id": prolific_id})
        if not user:
            user_rows = user_df[user_df["user_id"] == prolific_id]
            phases = {
                "static": {"batches": {}, "completed": False},
                "interactive": {"batches": {}, "completed": False},
                "finetuned": {"batches": {}, "completed": False},
            }
            for _, row in user_rows.iterrows():
                # Example: "static_1", "interactive_3"
                full_type = row["type"]
                phase_type, batch_id = full_type.split("_")  # phase_type="static", batch_id="1"

                # Create batch container if not exists
                if batch_id not in phases[phase_type]["batches"]:
                    phases[phase_type]["batches"][batch_id] = {
                        "completed": False,
                        "approved": False,
                        "abstracts": {}
                    }

                # Only static rows have precomputed terms
                if phase_type == "static":
                    raw_terms = str(row["terms"]).strip().strip("[]")
                    term_list = [t.strip() for t in raw_terms.split(",") if t.strip()]
                    structured_terms = [
                        {"term": t, "familiar": None, "extra_information": None}
                        for t in term_list
                    ]
                else:
                    structured_terms = []
                abstract_key = str(row["abstract_id"])

                phases[phase_type]["batches"][batch_id][abstract_key] = {
                    "abstract_title": row["abstract_title"],
                    "abstract": row["abstract"],
                    "main_idea_question": row["main_idea_question"],
                    "method_question": row["method_question"],
                    "result_question": row["result_question"],
                    "short_answers": {
                        "main_idea": "",
                        "methods": "",
                        "results": "",
                    },
                    "term_familarity": structured_terms,
                    "human_written_pls": row["human_written"],
                    "completed": False,
                }


            users_collection.insert_one({
                "prolific_id": prolific_id,
                "created_at": datetime.datetime.utcnow(),
                "accepted_terms": True,
                "phases": phases
            })
            user = users_collection.find_one({"prolific_id": prolific_id}) 

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
    if "seen_static_instructions" not in st.session_state:
        st.session_state.seen_static_instructions = False
    if "seen_interactive_instructions" not in st.session_state:
        st.session_state.seen_interactive_instructions = False
    if "seen_finetuned_instructions" not in st.session_state:
        st.session_state.seen_finetuned_instructions = False
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

    if st.session_state.current_page == "terms":
        run_terms(st.session_state.prolific_id)
    else:
        run_chatbot(st.session_state.prolific_id)
