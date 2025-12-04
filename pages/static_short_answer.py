import streamlit as st
from pymongo import MongoClient
from datetime import datetime
import sys
from navigation import render_nav
print("=== SESSION STATE DUMP ===", file=sys.stderr)
for k, v in st.session_state.items():
    print(f"{k}: {v}", file=sys.stderr)
print("===========================", file=sys.stderr)
MIN_CHARS = 75
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
            st.session_state.logged_in = False
            st.session_state.prolific_id = None
            st.switch_page("app.py")

def accumulate_question_time():
    """Add elapsed time to the current question."""
    if "question_start_time" not in st.session_state:
        return
    elapsed = (datetime.utcnow() - st.session_state.question_start_time).total_seconds()
    key_map = {
        0: "main_idea_time",
        1: "method_time",
        2: "attention_time",
        3: "result_time"
    }
    q_key = key_map.get(st.session_state.qa_index)
    if q_key:
        st.session_state[q_key] = st.session_state.get(q_key, 0) + elapsed
    st.session_state.question_start_time = datetime.utcnow()


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

    user = users_collection.find_one({"prolific_id": data["prolific_id"]})
    phase = "static"
    abstract_info = user["phases"][phase]["batches"][data["batch_id"]]["abstracts"][data["abstract_id"]]
    with st.sidebar:
        st.write(f"**MTurk ID:** `{data['prolific_id']}`")
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
        2. You must answer **4 short-answer questions**, each with **more than 75 characters**.  
        - After completing a question, click **Next Question** to proceed.  
        3. **Do NOT copy text from the SUMMARY** or provide irrelevant answers that has nothing to do with the question — doing so may risk your compensation.  
        4. After finishing all questions, click outside the text box to activate the **Submit** button, then click **Submit** to continue.

        **Note:**  
        You may use the **Back** button to return to the term-familiarity page or to revisit a previous short-answer question *within this same abstract*.  
        """)

    if "summary_font_size" not in st.session_state:
        st.session_state.summary_font_size = 16

    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.title("SUMMARY")

        # Font size buttons
        b1, b2, b3 = st.columns([0.25, 0.55, 0.20])
        with b1:
            if st.button("Decrease Text Size"):
                st.session_state.summary_font_size = max(12, st.session_state.summary_font_size - 2)
                st.rerun()
        with b3:
            if st.button("Increase Text Size"):
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
        st.title("Short Answer Questions")
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

        # Feedback dict
        if "feedback" not in st.session_state:
            st.session_state.feedback = {"main_idea": "", "method": "", "attention": "", "result": ""}

        questions = [
            {"key": "main_idea", "label": f"🧠 {abstract_info['main_idea_question']}"},
            {"key": "method", "label": f"🧪 {abstract_info['method_question']}"},
            {
            "key": "attention",
                "label": (
                    "⚠️ Attention Check\n\n"
                    "To confirm you are paying attention, please type the following "
                    "sentence exactly as written:\n\n"
                    "**\"I have read all instructions and fully understood what I must do for this task.\"**"
                )
            },
            {"key": "result", "label": f"📊 {abstract_info['result_question']}"}
        ]

        q = questions[st.session_state.qa_index]
        key = q["key"]

        # Question text area
        st.subheader(q["label"])
        box_key = f"{key}_box"
        if box_key not in st.session_state:
            st.session_state[box_key] = st.session_state.feedback[key]
        st.text_area(
            "",
            key=box_key,
            on_change=lambda k=key, b=box_key: st.session_state.feedback.__setitem__(
                k, st.session_state[b]
            )
        )
        st.caption(f"{len(st.session_state.feedback[key])} characters")
        st.markdown(
            f"<span style='color:#555;'>Each response must be more than {MIN_CHARS} characters. Click outside textbox to see character count.</span>",
            unsafe_allow_html=True
        )

        completed = sum(
            len(st.session_state.feedback[k].strip()) >= MIN_CHARS
            for k in ["main_idea", "method", "attention", "result"]
        )

        st.markdown(
            f"<div style='font-size:0.9rem; color:#444;'><strong>Questions completed:</strong> {completed} / 4</div>",
            unsafe_allow_html=True
        )

        # Navigation
        nav1, nav2, nav3 = st.columns([1, 2, 1])

        with nav1:
            if st.session_state.qa_index > 0 and st.button("⬅ Previous Question"):
                st.session_state.qa_index -= 1
                st.rerun()

        with nav3:
            if st.session_state.qa_index < 3:
                if st.button("Next Question ➡"):
                    st.session_state.qa_index += 1
                    st.rerun()
            else:
                all_filled = completed == 4

                if st.button("Submit", disabled=not all_filled):
                    accumulate_question_time()
                    # Save
                    feedback_data = {
                        "main_idea": st.session_state.feedback["main_idea"].strip(),
                        "methods": st.session_state.feedback["method"].strip(),
                        "attention": st.session_state.feedback["attention"].strip(),
                        "results": st.session_state.feedback["result"].strip(),
                        "submitted_at": datetime.utcnow(),
                        "time_main_idea": st.session_state.get("main_idea_time", 0),
                        "time_method": st.session_state.get("method_time", 0),
                        "time_attention": st.session_state.get("attention_time", 0),
                        "time_result": st.session_state.get("result_time", 0),
                    }
                    users_collection.update_one(
                        {"prolific_id": data['prolific_id']},
                        {"$set": {
                            f"phases.static.batches.{data['batch_id']}.abstracts.{data['abstract_id']}.short_answers": feedback_data,
                            f"phases.static.batches.{data['batch_id']}.abstracts.{data['abstract_id']}.feedback_submitted": True
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
