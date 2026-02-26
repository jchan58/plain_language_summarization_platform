import streamlit as st
from pymongo import MongoClient
from datetime import datetime
import sys
from navigation import render_nav
print("=== SESSION STATE DUMP ===", file=sys.stderr)
for k, v in st.session_state.items():
    print(f"{k}: {v}", file=sys.stderr)
print("===========================", file=sys.stderr)
st.markdown(
    """
    <style>
        [data-testid="stSidebarNav"] {display: none;}
    </style>
    """,
    unsafe_allow_html=True
)

st.set_page_config(layout="wide")

if "q1_time" not in st.session_state:
    st.session_state.q1_time = 0
    st.session_state.q2_time = 0
    st.session_state.q3_time = 0
    st.session_state.q4_time = 0
    st.session_state.q5_time = 0

@st.cache_resource
def get_mongo_client():
    return MongoClient(st.secrets["MONGO_URI"])

# connect to MongoDB
MONGO_URI = st.secrets["MONGO_URI"]
client = MongoClient(MONGO_URI)
db = client["pls"]
users_collection = db["users"]

@st.fragment
def summary_fragment(pls_text, font_size):
    st.markdown(
        f"""
        <div class="no-select" style="
            background-color:#e8f4ff;
            padding: 1.1rem 1.3rem;
            border-radius: 0.6rem;
            border: 1px solid #dfe1e5;
            max-height: 550px;
            overflow-y: auto;
            font-size: {font_size}px;
            line-height: 1.55;
        ">
            <div style="line-height: 1.55;">
                {pls_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

@st.cache_data
def load_abstract_info(prolific_id, batch_id, abstract_id):
    user = users_collection.find_one({"prolific_id": prolific_id})
    if not user:
        return None
    return user["phases"]["static"]["batches"][batch_id]["abstracts"][abstract_id]

@st.dialog("Are you sure you want to log out?", dismissible=False)
def logout_confirm_dialog(prolific_id):
    # st.markdown(
    #     "Your progress will not be saved until you finish this abstract, which happens after you complete the **Compare SUMMARY to ABSTRACT Questionnaire**, click the **Next Abstract button**, and **confirm** that you want to move on.\n\n"
    #     "If you log out before then, you will have to start this abstract over."
    # )
    st.markdown(
        "Your progress will not be saved until you finish this abstract, which happens after you complete the **Compare SUMMARY to ABSTRACT Questionnaire**, click the **Next Batch button**, and **confirm** that you want to move on.\n\n"
        "If you log out before then, you will have to start this abstract over."
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Stay on page"):
            st.session_state.show_logout_dialog = False
            st.rerun()

    with col2:
        if st.button("Logout"):
            st.session_state.show_logout_dialog = False            
            st.session_state.logged_in = False
            st.session_state.prolific_id = None
            st.switch_page("app.py")

def accumulate_question_time(index):
    if "question_start_time" not in st.session_state:
        return

    elapsed = (datetime.utcnow() - st.session_state.question_start_time).total_seconds()

    key_map = {
        0: "q1_time",
        1: "q2_time",
        2: "q3_time",
        3: "q4_time",
        4: "q5_time"
    }

    q_key = key_map.get(index)
    if q_key:
        st.session_state[q_key] = st.session_state.get(q_key, 0) + elapsed

    st.session_state.question_start_time = datetime.utcnow()

def parse_choices(s):
    return [x.strip() for x in s.split(";") if x.strip()]

def show_progress():
    if "progress_info" in st.session_state:
        progress = st.session_state.progress_info
        current = progress.get("current_index", 0)
        total = progress.get("total", 1)
        st.progress(current / total)
        st.caption(f"Progress: {current} of {total} abstracts completed")

def run_feedback():
    data = {
        "title": st.session_state.get("abstract_title", ""),
        "abstract": st.session_state.get("current_abstract", ""),
        "pls": st.session_state.get("human_written_pls", ""),
        "prolific_id": st.session_state.get("prolific_id", ""),
        "abstract_id": st.session_state.get("current_abstract_id", ""),
        "batch_id": st.session_state.get("batch_id", 0), 
        "full_type": st.session_state.get("full_type", None)
    }

    abstract_info = load_abstract_info(
        data["prolific_id"], 
        data["batch_id"], 
        data["abstract_id"]
    )

    # ==================================================
    # ✅ RESET TIMING + ANSWERS WHEN ABSTRACT CHANGES
    # ==================================================
    if st.session_state.get("sata_for_abstract") != data["abstract_id"]:
        # reset per-question timing
        for k in ["q1_time", "q2_time", "q3_time", "q4_time", "q5_time"]:
            st.session_state[k] = 0

        # reset timer + navigation
        st.session_state.question_start_time = datetime.utcnow()
        st.session_state.qa_index = 0

        # reset SATA answers
        st.session_state.sata_answers = {
            "q1": [], "q2": [], "q3": [], "q4": [], "q5": []
        }

        st.session_state.sata_for_abstract = data["abstract_id"]
    # ==================================================

    with st.sidebar:
        st.write(f"**Prolific ID:** `{data['prolific_id']}`")
        if st.button("Logout"):
            st.session_state.show_logout_dialog = True
        if st.session_state.get("show_logout_dialog", False):
            st.session_state.show_logout_dialog = False 
            logout_confirm_dialog(data['prolific_id'])

    st.title("Answer Questions About SUMMARY")
    current_index = st.session_state.progress_info["current_index"]
    total = st.session_state.progress_info["total"]
    st.progress(current_index / total if total > 0 else 0)
    st.caption(f"Completed {current_index} of {total} abstracts")

    with st.expander("📝 Instructions", expanded=True):
        st.markdown("""
        1. Read the SUMMARY shown below.  
        2. Then answer all **5 select all that apply questions**.  
        3. Click **Next Question** to proceed and **Submit** when finished.
        """)

    if "summary_font_size" not in st.session_state:
        st.session_state.summary_font_size = 16

    col1, col2 = st.columns([1, 1], gap="large")

    # ---------------- SUMMARY ----------------
    with col1:
        st.title("SUMMARY")
        b1, _, b3 = st.columns([0.25, 0.65, 0.10])

        with b1:
            if st.button("A-"):
                st.session_state.summary_font_size = max(12, st.session_state.summary_font_size - 2)
                st.rerun()
        with b3:
            if st.button("A+"):
                st.session_state.summary_font_size = min(30, st.session_state.summary_font_size + 2)
                st.rerun()

        summary_fragment(data["pls"], st.session_state.summary_font_size)

    # ---------------- QUESTIONS ----------------
    with col2:
        st.title("Select All That Apply (SATA) Questions")

        if "question_start_time" not in st.session_state:
            st.session_state.question_start_time = datetime.utcnow()

        questions = [
            {"key": "q1", "text": abstract_info["question_1"],
             "choices": parse_choices(abstract_info["question_1_answers_choices"])},
            {"key": "q2", "text": abstract_info["question_2"],
             "choices": parse_choices(abstract_info["question_2_answers_choices"])},
            {"key": "q3", "text": abstract_info["question_3"],
             "choices": parse_choices(abstract_info["question_3_answers_choices"])},
            {"key": "q4", "text": abstract_info["question_4"],
             "choices": parse_choices(abstract_info["question_4_answers_choices"])},
            {"key": "q5", "text": abstract_info["question_5"],
             "choices": parse_choices(abstract_info["question_5_answers_choices"])},
        ]

        q = questions[st.session_state.qa_index]
        st.subheader(q["text"])

        selected = []
        for choice in q["choices"]:
            if st.checkbox(
                choice,
                key=f"{data['abstract_id']}_{q['key']}_{hash(choice)}",
                value=choice in st.session_state.sata_answers[q["key"]]
            ):
                selected.append(choice)

        st.session_state.sata_answers[q["key"]] = selected
        completed = sum(len(v) > 0 for v in st.session_state.sata_answers.values())
        st.markdown(f"**Questions completed:** {completed} / 5")

        nav1, _, nav3 = st.columns([1, 2, 1])

        with nav1:
            if st.session_state.qa_index > 0 and st.button("⬅ Previous Question"):
                accumulate_question_time(st.session_state.qa_index)
                st.session_state.qa_index -= 1
                st.rerun()

        with nav3:
            if st.session_state.qa_index < 4:
                if st.button("Next Question ➡"):
                    accumulate_question_time(st.session_state.qa_index)
                    st.session_state.qa_index += 1
                    st.rerun()
            else:
                if st.button("Submit", disabled=completed < 5):
                    accumulate_question_time(st.session_state.qa_index)

                    feedback_data = {
                        "sata_answers": st.session_state.sata_answers,
                        "submitted_at": datetime.utcnow(),
                        "time_q1": st.session_state.q1_time,
                        "time_q2": st.session_state.q2_time,
                        "time_q3": st.session_state.q3_time,
                        "time_q4": st.session_state.q4_time,
                        "time_q5": st.session_state.q5_time,
                    }

                    users_collection.update_one(
                        {"prolific_id": data["prolific_id"]},
                        {"$set": {
                            f"phases.static.batches.{data['batch_id']}.abstracts.{data['abstract_id']}.sata": feedback_data,
                            f"phases.static.batches.{data['batch_id']}.abstracts.{data['abstract_id']}.sata_submitted": True
                        }}
                    )

                    st.switch_page("pages/static_likert.py")

run_feedback()
