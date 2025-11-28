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

def accumulate_question_time():
    """Add elapsed time to the current question."""
    if "question_start_time" not in st.session_state:
        return

    elapsed = (datetime.utcnow() - st.session_state.question_start_time).total_seconds()

    key_map = {
        0: "main_idea_time",
        1: "method_time",
        2: "result_time"
    }
    q_key = key_map.get(st.session_state.qa_index)

    if q_key:
        st.session_state[q_key] = st.session_state.get(q_key, 0) + elapsed
    st.session_state.question_start_time = datetime.utcnow()


def run_feedback():
    render_nav()
    with st.sidebar:
        if "last_completed_abstract" in st.session_state:
            user_info = st.session_state.last_completed_abstract
            st.markdown(f"**MTurk ID:** `{user_info['prolific_id']}`")

        if st.button("Logout"):
            for key in [
                "last_completed_abstract", "feedback", "survey_context",
                "progress_info", "messages", "show_summary",
                "generated_summary", "question_count",
                "main_idea_time", "method_time", "result_time",
                "question_start_time", "last_qa_index",
            ]:
                st.session_state.pop(key, None)
            st.switch_page("app.py")

    st.title("Answer Questions About SUMMARY")

    data = st.session_state.last_completed_abstract
    prolific_id = data["prolific_id"]
    abstract_id = data["abstract_id"]
    current = st.session_state.progress_info["current"]
    total = st.session_state.progress_info["total"]
    progress_ratio = current / total if total > 0 else 0

    st.progress(progress_ratio)
    st.caption(f"Completed {current} of {total} abstracts")
    st.markdown(
        """
        ### 📝 Instructions
        1. Please read the summary shown below.
        2. Answer each question carefully.  
        3. **Do NOT copy from the summary.**  
        4. Click **Next** after finishing all questions.  
        """
    )

    if "summary_font_size" not in st.session_state:
        st.session_state.summary_font_size = 18

    if "last_completed_abstract" not in st.session_state:
        st.warning("Please complete the interactive session first.")
        st.stop()

    col1, col2 = st.columns([1, 1], gap="large")

    # ------------------------
    # SUMMARY COLUMN
    # ------------------------
    with col1:
        st.title("SUMMARY")
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

        st.markdown(
            f"""
            <div style="
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

    # ------------------------
    # QUESTIONS COLUMN
    # ------------------------
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

        # Ensure answers dict exists
        if "feedback" not in st.session_state:
            st.session_state.feedback = {"main_idea": "", "method": "", "result": ""}

        questions = [
            {"key": "main_idea", "label": "🧠 What did the researchers want to find out?"},
            {"key": "method", "label": "🧪 What method did the study use?"},
            {"key": "result", "label": "📊 What was the result of the study?"}
        ]

        q = questions[st.session_state.qa_index]
        key = q["key"]

        st.subheader(q["label"])
        st.text_area(
            "",
            key=f"{key}_box",
            value=st.session_state.feedback[key],
            on_change=lambda k=key: st.session_state.feedback.__setitem__(k, st.session_state[f"{k}_box"])
        )

        st.caption(f"{len(st.session_state.feedback[key])} characters")
        st.markdown(
            f"<span style='color:#555;'>Each response must be at least {MIN_CHARS} characters.</span>",
            unsafe_allow_html=True
        )

        completed = sum(
            len(st.session_state.feedback[k].strip()) >= MIN_CHARS
            for k in ["main_idea", "method", "result"]
        )

        st.markdown(
            f"<div style='margin-top:0.4rem; font-size:0.9rem; color:#444;'>"
            f"<strong>Questions completed:</strong> {completed} / 3"
            f"</div>",
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
            if st.session_state.qa_index < 2:
                if st.button("Next Question ➡"):
                    accumulate_question_time()
                    st.session_state.qa_index += 1
                    st.rerun()

            else:
                all_filled = completed == 3

                if st.button("Submit", disabled=not all_filled):

                    # Final time accumulation
                    accumulate_question_time()

                    feedback_data = {
                        "main_idea": st.session_state.feedback["main_idea"].strip(),
                        "methods": st.session_state.feedback["method"].strip(),
                        "results": st.session_state.feedback["result"].strip(),
                        "submitted_at": datetime.utcnow(),
                        "time_main_idea": st.session_state.get("main_idea_time", 0),
                        "time_method": st.session_state.get("method_time", 0),
                        "time_result": st.session_state.get("result_time", 0),
                    }

                    client = MongoClient(st.secrets["MONGO_URI"])
                    db = client["pls"]
                    users_collection = db["users"]

                    users_collection.update_one(
                        {"prolific_id": prolific_id},
                        {"$set": {
                            f"phases.interactive.abstracts.{abstract_id}.short_answers": feedback_data,
                            f"phases.interactive.abstracts.{abstract_id}.feedback_submitted": True
                        }}
                    )

                    st.session_state.survey_context = {
                        "abstract_title": data["title"],
                        "abstract": data["abstract"],
                        "pls": data["pls"],
                        "prolific_id": prolific_id,
                        "abstract_id": abstract_id,
                    }

                    st.session_state.progress_info = {
                        "current": current,
                        "total": total
                    }

                    st.switch_page("pages/likert.py")


run_feedback()
