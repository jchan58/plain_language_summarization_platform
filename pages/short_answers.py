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
@st.cache_resource
def get_mongo_client():
    return MongoClient(st.secrets["MONGO_URI"])

# connect to MongoDB
MONGO_URI = st.secrets["MONGO_URI"]
client = MongoClient(MONGO_URI)
db = client["pls"]
users_collection = db["users"]

def parse_choices(s):
    return [x.strip() for x in s.split(";") if x.strip()]

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

@st.dialog("Are you sure you want to log out?", dismissible=False)
def logout_confirm_dialog(prolific_id):
    # st.markdown(
    #     "Your progress will not be saved until you finish this abstract, which happens after you complete the **Compare AI-Generated SUMMARY to ABSTRACT Questionnaire**, click the **Next Abstract button**, and **confirm** that you want to move on.\n\n"
    #     "If you log out before then, you will have to start this abstract over."
    # )
    st.markdown(
        "Your progress will not be saved until you finish this abstract, which happens after you complete the **Compare AI-Generated SUMMARY to ABSTRACT Questionnaire**, click the **Next Batch button**, and **confirm** that you want to move on.\n\n"
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

def run_feedback():
    data = st.session_state.last_completed_abstract
    prolific_id = data["prolific_id"]
    abstract_id = data["abstract_id"]
    batch_id = data['batch_id']
    full_type = data['full_type']
    user = users_collection.find_one({"prolific_id": prolific_id})
    phase = "interactive"
    abstract_info = user["phases"][phase]["batches"][batch_id]["abstracts"][abstract_id]
    with st.sidebar:
        st.write(f"**MTurk ID:** `{prolific_id}`")
        if st.button("Logout"):
            st.session_state.show_logout_dialog = True
        if st.session_state.get("show_logout_dialog", False):
            st.session_state.show_logout_dialog = False 
            logout_confirm_dialog(prolific_id)
    st.title("Answer Questions About AI-Generated SUMMARY")
    current = st.session_state.progress_info["current"]
    total = st.session_state.progress_info["total"]
    progress_ratio = current / total if total > 0 else 0

    st.progress(progress_ratio)
    st.caption(f"Completed {current} of {total} abstracts")
    with st.expander("📝 Instructions", expanded=True):
        st.markdown("""
        1. Read the AI-Generated SUMMARY shown below.  
        2. Then answer all **5 select all that apply questions** .  
            - After completing a question, click **Next Question** to proceed.  
        3. After finishing all questions, click **Submit** button to continue.

        **Note:**  
        You may use the **Previous Question** button to revisit the previous select all that apply question.  
        """)
    if "summary_font_size" not in st.session_state:
        st.session_state.summary_font_size = 18

    if "last_completed_abstract" not in st.session_state:
        st.warning("Please complete the interactive session first.")
        st.stop()

    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.title("AI-Generated SUMMARY")
        btn_col1, btn_col2, btn_col3 = st.columns([0.25, 0.55, 0.20])

        with btn_col1:
            if st.button("Decrease text size"):
                st.session_state.summary_font_size = max(12, st.session_state.summary_font_size - 2)
                st.rerun()

        with btn_col2:
            st.write("")

        with btn_col3:
            if st.button("Increase text size"):
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
        st.markdown(
            f"""
            <div class="no-select" style="
                background-color:#e8f4ff;
                padding: 1.1rem 1.3rem;
                border-radius: 0.6rem;
                border: 1px solid #dfe1e5;
                max-height: 550px;
                overflow-y: auto;
                font-size: {st.session_state.summary_font_size}px;
                line-height: 1.55;
            ">
                <div style="line-height: 1.55;">
                    {data['pls']}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.title("Select All That Apply (SATA) Questions")

        if "qa_index" not in st.session_state:
            st.session_state.qa_index = 0

        # Start timer if first load OR if we switched questions
        if "question_start_time" not in st.session_state:
            st.session_state.question_start_time = datetime.utcnow()
            st.session_state.last_qa_index = st.session_state.qa_index
        else:
            if st.session_state.last_qa_index != st.session_state.qa_index:
                accumulate_question_time()
                st.session_state.last_qa_index = st.session_state.qa_index

        # Ensure answers dict exists
        if "feedback" not in st.session_state:
            st.session_state.feedback = {"main_idea": "", "method": "", "attention": "", "result": ""}

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
            }
        ]

        if "sata_for_abstract" not in st.session_state:
            st.session_state.sata_for_abstract = None

        if st.session_state.sata_for_abstract != abstract_id:
            st.session_state.sata_answers = {q["key"]: [] for q in questions}
            st.session_state.qa_index = 0
            st.session_state.question_start_time = datetime.utcnow()

            for k in ["q1_time", "q2_time", "q3_time", "q4_time", "q5_time"]:
                st.session_state[k] = 0

            st.session_state.sata_for_abstract = abstract_id

        q = questions[st.session_state.qa_index]
        st.subheader(q["text"])

        selected = []
        for choice in q["choices"]:
            checkbox_key = f"{abstract_id}_{q['key']}_{hash(choice)}"
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

                    # Final time accumulation
                    accumulate_question_time()

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
                            f"phases.interactive.batches.{data['batch_id']}.abstracts.{data['abstract_id']}.sata": feedback_data,
                            f"phases.interactive.batches.{data['batch_id']}.abstracts.{data['abstract_id']}.sata_submitted": True
                        }}
                    )

                    st.session_state.survey_context = {
                        "abstract_title": data["title"],
                        "abstract": data["abstract"],
                        "pls": data["pls"],
                        "prolific_id": prolific_id,
                        "abstract_id": abstract_id,
                        "batch_id": batch_id, 
                        "full_type": full_type
                    }

                    st.session_state.progress_info = {
                        "current": current,
                        "total": total
                    }

                    users_collection.update_one(
                        {"prolific_id": prolific_id},
                        {"$set": {
                            "last_page": "short_answers",
                            "last_batch": batch_id,
                            "last_abs_id": abstract_id,
                            "last_full_type": full_type
                        }}
                    )
                    st.switch_page("pages/likert.py")


run_feedback()


