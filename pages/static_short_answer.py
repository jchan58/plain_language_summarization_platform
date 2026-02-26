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

def accumulate_question_time():
    """Add elapsed time to the current question."""
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
    q_key = key_map.get(st.session_state.qa_index)
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
    progress_ratio = current_index / total if total > 0 else 0
    st.progress(progress_ratio)
    st.caption(f"Completed {current_index} of {total} abstracts")
    with st.expander("📝 Instructions", expanded=True):
        st.markdown("""
        1. Read the SUMMARY shown below.  
        2. Then answer all **5 select all that apply questions** .  
            - After completing a question, click **Next Question** to proceed.  
        3. After finishing all questions, click **Submit** button to continue.

        **Note:**  
        You may use the **Previous Question** button to revisit the previous select all that apply question.  
        """)

    if "summary_font_size" not in st.session_state:
        st.session_state.summary_font_size = 16

    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.title("SUMMARY")

        # Font size buttons
        b1, b2, b3 = st.columns([0.25, 0.65, 0.10])
        with b1:
            if st.button("A-"):
                st.session_state.summary_font_size = max(12, st.session_state.summary_font_size - 2)
                st.rerun()
        with b3:
            if st.button("A+"):
                st.session_state.summary_font_size = min(30, st.session_state.summary_font_size + 2)
                st.rerun()

        st.markdown("""
        <style>
        .no-select {
            -webkit-user-select: none;  
            -moz-user-select: none;  
            -ms-user-select: none;     
            user-select: none;          
        }

        .no-select * {
            -webkit-user-select: none !important;
            user-select: none !important;
        }

        /* Optional: disable right-click */
        .no-select {
            -webkit-touch-callout: none;
        }
        </style>
        """, unsafe_allow_html=True)
        summary_fragment(data["pls"], st.session_state.summary_font_size)
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        if st.button("⬅️ Back"):
            st.session_state.stage_static = "extra_info"
            st.switch_page("pages/term_familarity_page.py")
    with col2:
        st.title("Select All That Apply (SATA) Questions")
        
        if "qa_index" not in st.session_state:
            st.session_state.qa_index = 0

        if "last_qa_index" not in st.session_state:
            st.session_state.last_qa_index = 0
        
        if "question_start_time" not in st.session_state:
            st.session_state.question_start_time = datetime.utcnow()
        else:
            if st.session_state.last_qa_index != st.session_state.qa_index:
                accumulate_question_time()
                st.session_state.last_qa_index = st.session_state.qa_index

        questions = [
            {
                "key": "q1",
                "text": abstract_info["question_1"],
                "choices": parse_choices(abstract_info["question_1_answers_choices"]),
                "correct": parse_choices(abstract_info["question_1_correct_answers"])
            },
            {
                "key": "q2",
                "text": abstract_info["question_2"],
                "choices": parse_choices(abstract_info["question_2_answers_choices"]),
                "correct": parse_choices(abstract_info["question_2_correct_answers"])
            },
            {
                "key": "q3",
                "text": abstract_info["question_3"],
                "choices": parse_choices(abstract_info["question_3_answers_choices"]),
                "correct": parse_choices(abstract_info["question_3_correct_answers"])
            },
            {
                "key": "q4",
                "text": abstract_info["question_4"],
                "choices": parse_choices(abstract_info["question_4_answers_choices"]),
                "correct": parse_choices(abstract_info["question_4_correct_answers"])
            },
            {
                "key": "q5",
                "text": abstract_info["question_5"],
                "choices": parse_choices(abstract_info["question_5_answers_choices"]),
                "correct": parse_choices(abstract_info["question_5_correct_answers"])
            },
        ]

        if "sata_answers" not in st.session_state:
            st.session_state.sata_answers = {q["key"]: [] for q in questions}

        q = questions[st.session_state.qa_index]
        st.subheader(q["text"])

        selected = []
        for choice in q["choices"]:
            checkbox_key = f"{data['abstract_id']}_{q['key']}_{hash(choice)}"
            checked = st.checkbox(
                choice,
                key=checkbox_key,
                value=choice in st.session_state.sata_answers[q["key"]]
            )
            if checked:
                selected.append(choice)

        st.session_state.sata_answers[q["key"]] = selected
        completed = sum(
            len(st.session_state.sata_answers[q["key"]]) > 0
            for q in questions
        )

        st.markdown(
            f"<div><strong>Questions completed:</strong> {completed} / {len(questions)}</div>",
            unsafe_allow_html=True
        )

        # Navigation
        nav1, nav2, nav3 = st.columns([1, 2, 1])

        with nav1:
            if st.session_state.qa_index > 0:
                if st.button("⬅ Previous Question"):
                    accumulate_question_time()
                    st.session_state.qa_index -= 1
                    st.rerun()

        with nav3:
            if st.session_state.qa_index < len(questions) - 1:
                if st.button("Next Question ➡"):
                    accumulate_question_time()
                    st.session_state.qa_index += 1
                    st.rerun()
            else:
                all_filled = completed == 5
                if st.button("Submit", disabled=not all_filled):
                    # Capture time for the final question (Q5) before submitting
                    accumulate_question_time()
                    # Save
                    feedback_data = {
                        "sata_answers": st.session_state.sata_answers,
                        "submitted_at": datetime.utcnow(),
                        "time_q1": st.session_state.get("q1_time", 0),
                        "time_q2": st.session_state.get("q2_time", 0),
                        "time_q3": st.session_state.get("q3_time", 0),
                        "time_q4": st.session_state.get("q4_time", 0),
                        "time_q5": st.session_state.get("q5_time", 0),
                    }
                    users_collection.update_one(
                        {"prolific_id": data['prolific_id']},
                        {"$set": {
                            f"phases.static.batches.{data['batch_id']}.abstracts.{data['abstract_id']}.sata": feedback_data,
                            f"phases.static.batches.{data['batch_id']}.abstracts.{data['abstract_id']}.sata_submitted": True
                        }}
                    )

                    users_collection.update_one(
                        {"prolific_id": data['prolific_id']},
                        {"$set": {
                            "last_page": "static_short_answer",
                            "last_batch": data["batch_id"],
                            "last_abs_id": data["abstract_id"],
                            "last_full_type": data["full_type"]
                        }}
                    )
                    st.session_state.survey_context = {
                        "abstract_title": data["title"],
                        "abstract": data["abstract"],
                        "pls": data["pls"],
                        "prolific_id": data["prolific_id"],
                        "abstract_id": data["abstract_id"], 
                        "batch_id": data["batch_id"], 
                        "full_type": data["full_type"]
                    }
                    st.session_state.progress_info = {
                        "current_index": current_index,
                        "total": total
                    }
                    st.switch_page("pages/static_likert.py")


run_feedback()
