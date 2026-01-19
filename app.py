import streamlit as st
from pymongo import MongoClient
import datetime
import pandas as pd
from openai import OpenAI
from pages.chatbot import run_chatbot
from pages.term_familarity_page import run_terms
import ftfy
import re

# order of the batches
BATCH_ORDER = [
    "static_1",
    "static_2",
    "interactive_3",
    "interactive_4",
    "finetuned_5",
    "finetuned_6",
]

# passcodes for each batch, first batch has none
PASSCODES = {
    "static_1": None,          
    "static_2": "ABC123",
    "interactive_3": "DOG721",
    "interactive_4": "CAT999",
    "finetuned_5": "BLUE425",
    "finetuned_6": "RED591", 
}

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
user_df = pd.read_csv("final_user_batches.csv", encoding="latin1")

# determine what batch user will start off with 
def get_current_batch(user_doc):
    phases = user_doc.get("phases", {})

    for full_type in BATCH_ORDER:
        phase_type, batch_id = full_type.split("_")
        phase = phases.get(phase_type, {})
        batches = phase.get("batches", {})
        batch = batches.get(batch_id)

        # Skip if this batch doesn't exist for this user
        if batch is None:
            continue

        # get the first incomplete batch 
        if not batch.get("completed", False):
            return {
                "full_type": full_type,
                "phase_type": phase_type,
                "batch_id": batch_id,
                "unlocked": batch.get("unlocked", False),
            }

    return None

if "seen_pilot_intro" not in st.session_state:
    st.session_state.seen_pilot_intro = False

if not st.session_state.seen_pilot_intro:

    @st.dialog("Pilot Study Instructions", width="large", dismissible=False)
    def pilot_dialog():
        st.markdown("""
        ## Pilot Study Instructions

        You are participating in a **pilot study** with two phases:

        1. **Static Phase (First Phase)**
        2. **Interactive Phase (Second Phase)**

        Each phase contains **one abstract**.

        Instructions for each phase will be shown before you start. **Please read them carefully.**

        ---

        ## Timing Instructions for the Pilot Study

        Although the system automatically records time, during the pilot study you must also  
        **manually track your time**.

        - Please use a stopwatch, phone timer, or clock.
        - Record how long each phase takes in **seconds**.

        Manually record:
        - Time for the entire **Static Phase**
        - Time for the entire **Interactive Phase**
        - Time for the **Select All That Apply (SATA) questions section** should be recorded separately

        You will be asked to provide these recordings before moving on to the **Next Batch**.

        ---

        If you have any suggestions or comments to improve this study, please mention it in the feedback section for each phase.
        Thank you for helping us improve this study. **Please click the continue button and then login with your preferred email address to start the study.**
        """)

        if st.button("Continue"):
            st.session_state.seen_pilot_intro = True
            st.rerun()

    pilot_dialog()
    st.stop()

# check if the user exists in db if they don't 
if not st.session_state.get("logged_in", False):
    st.title("Making Research Articles Easier to Read – Pilot Study")
    st.markdown("""
    By entering your email address you agree to our [Terms and Conditions](https://docs.google.com/document/d/1wfvGWg69Vg3xroLDxpJXwe1_KWY72w0Z4ut59hA5iTM/edit?usp=sharing).
    """, unsafe_allow_html=True)
    # By entering your Mturk ID you agree to our [Terms and Conditions](https://docs.google.com/document/d/1wfvGWg69Vg3xroLDxpJXwe1_KWY72w0Z4ut59hA5iTM/edit?usp=sharing).
    # """, unsafe_allow_html=True)

    # prolific_id = st.text_input("Please enter your Mturk ID to begin annotating").strip()
    prolific_id = st.text_input("Please enter your email address to begin the pilot study").strip()
    if st.button("Enter"):
        if not prolific_id:
            st.error("Please enter your email address.")
            # st.error("Please enter your Mturk ID.")
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
                full_type = row["type"]      
                phase_type, batch_id = full_type.split("_") 
                if batch_id not in phases[phase_type]["batches"]:
                    # unlock the very first abstract
                    is_first_batch = (full_type == BATCH_ORDER[0])
                    phases[phase_type]["batches"][batch_id] = {
                        "completed": False,
                        "approved": False,
                        "unlocked": is_first_batch,
                        "abstracts": {},
                        "full_type": full_type,  
                    }

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
                phases[phase_type]["batches"][batch_id]["abstracts"][abstract_key]= {
                    "abstract_title": row["abstract_title"],
                    "abstract": re.sub(r"\s+", " ", ftfy.fix_text(row["abstract"])).strip(),
                    "main_idea_question": row["main_idea_question"],
                    "method_question": row["method_question"],
                    "result_question": row["result_question"],
                    "short_answers": {
                        "main_idea": "",
                        "methods": "",
                        "results": "",
                    },
                    "term_familarity": structured_terms,
                    "human_written_pls": re.sub(r"\s+", " ", ftfy.fix_text(row["human_written"])).strip(),
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

    user = users_collection.find_one({"prolific_id": st.session_state.prolific_id})
    current = get_current_batch(user)

    if current is None:
        st.success("🎉 You have completed all batches! Thank you!")
        st.stop()

    # passcode check 
    if not current["unlocked"]:
        # add in the sidebar
        with st.sidebar:
            st.write(f"**MTurk ID:** `{st.session_state.prolific_id}`")
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.prolific_id = None
                st.switch_page("app.py")
            batch_num = current["batch_id"]
        st.title(f"🔐 Enter Passcode to Unlock Batch {batch_num}")
        entered = st.text_input("Enter passcode for this batch:")
        if st.button("Unlock"):
            correct = PASSCODES.get(current["full_type"])

            if entered.strip() == correct:
                phase = current["phase_type"]
                batch_id = current["batch_id"]

                users_collection.update_one(
                    {"prolific_id": st.session_state.prolific_id},
                    {"$set": {f"phases.{phase}.batches.{batch_id}.unlocked": True}}
                )
                st.success("Unlocked! Loading batch…")
                st.rerun()
            else:
                st.error("Incorrect passcode. Please try again.")
        st.stop()

    # route to specific session based on type
    if current["phase_type"] == "static":
        run_terms(
            prolific_id=st.session_state.prolific_id,
            batch_id=current["batch_id"],
            full_type=current["full_type"]
        )
    else:
        run_chatbot(
            prolific_id=st.session_state.prolific_id,
            batch_id=current["batch_id"],
            full_type=current["full_type"]
        )
