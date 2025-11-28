import streamlit as st
from pymongo import MongoClient
from datetime import datetime
import sys
print("=== SESSION STATE DUMP ===", file=sys.stderr)
for k, v in st.session_state.items():
    print(f"{k}: {v}", file=sys.stderr)
print("===========================", file=sys.stderr)

# define minium character count 
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

def show_progress():
    if "progress_info" in st.session_state:
        progress = st.session_state.progress_info
        current = progress.get("current_index", 0)
        total = progress.get("total", 1)
        st.progress(current / total)
        st.caption(f"Progress: {current} of {total} abstracts completed")

def run_feedback():
    with st.sidebar:
        if "prolific_id" in st.session_state:
            st.markdown(f"**MTurk ID:** `{st.session_state.prolific_id}`")

        if st.button("Logout"):
            for key in [
                "feedback", "survey_context", "progress_info", "messages",
                "show_summary", "generated_summary", "question_count"
            ]:
                st.session_state.pop(key, None)
            st.switch_page("app.py")

    
    data = {
        "title": st.session_state.get("abstract_title", ""),
        "abstract": st.session_state.get("current_abstract", ""),
        "pls": st.session_state.get("human_written_pls", ""),
        "prolific_id": st.session_state.get("prolific_id", ""),
        "abstract_id": st.session_state.get("current_abstract_id", ""),
    }

    st.title("Answer Questions About SUMMARY")
    current_index = st.session_state.progress_info["current_index"]
    total = st.session_state.progress_info["total"]
    progress_ratio = current_index / total if total > 0 else 0
    st.progress(progress_ratio)
    st.caption(f"Completed {current_index} of {total} abstracts")
    st.markdown(
        """
        ### 📝 Instructions
        1. Please read the summary shown below, which was generated from the previous page.
        2. Answer the short answer questions to check your understanding.
        3. **DO NOT copy** from the summary, say “I don’t know,” or provide unrelated answers.
        4. After answering all questions, click **Submit** to continue.
        """
    )

    # Font size
    if "summary_font_size" not in st.session_state:
        st.session_state.summary_font_size = 1

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
                <div>{data['pls']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col2:
        st.title("Short Answer Questions")

        # Question index
        if "qa_index" not in st.session_state:
            st.session_state.qa_index = 0

        # Feedback dict
        if "feedback" not in st.session_state:
            st.session_state.feedback = {"main_idea": "", "method": "", "result": ""}

        # Questions list
        questions = [
            {"key": "main_idea", "label": "🧠 What did the researchers want to find out?"},
            {"key": "method", "label": "🧪 What method did the study use?"},
            {"key": "result", "label": "📊 What was the result of the study?"}
        ]

        q = questions[st.session_state.qa_index]
        key = q["key"]

        # Question text area
        st.subheader(q["label"])
        st.text_area(
            "",
            key=f"{key}_box",
            value=st.session_state.feedback[key],
            on_change=lambda k=key: st.session_state.feedback.__setitem__(
                k, st.session_state[f"{k}_box"]
            )
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
            f"<div style='font-size:0.9rem; color:#444;'><strong>Questions completed:</strong> {completed} / 3</div>",
            unsafe_allow_html=True
        )

        # Navigation
        nav1, nav2, nav3 = st.columns([1, 2, 1])

        with nav1:
            if st.session_state.qa_index > 0 and st.button("⬅ Previous Question"):
                st.session_state.qa_index -= 1
                st.rerun()

        with nav3:
            if st.session_state.qa_index < 2:
                if st.button("Next Question ➡"):
                    st.session_state.qa_index += 1
                    st.rerun()
            else:
                all_filled = completed == 3

                if st.button("Submit", disabled=not all_filled):
                    # Save
                    feedback_data = {
                        "main_idea": st.session_state.feedback["main_idea"].strip(),
                        "methods": st.session_state.feedback["method"].strip(),
                        "results": st.session_state.feedback["result"].strip(),
                        "submitted_at": datetime.utcnow()
                    }

                    client = MongoClient(st.secrets["MONGO_URI"])
                    users_collection = client["pls"]["users"]
                    users_collection.update_one(
                        {"prolific_id": data["prolific_id"]},
                        {"$set": {
                            f"phases.static.abstracts.{data['abstract_id']}.short_answers": feedback_data,
                            f"phases.static.abstracts.{data['abstract_id']}.feedback_submitted": True
                        }}
                    )

                    st.session_state.survey_context = {
                        "abstract_title": data["title"],
                        "abstract": data["abstract"],
                        "pls": data["pls"],
                        "prolific_id": data["prolific_id"],
                        "abstract_id": data["abstract_id"], 
                        "current": data["current"], 
                        "total": data["total"]
                    }
                    st.session_state.progress_info = {
                        "current": current,
                        "total": total
                    }
                    st.switch_page("pages/static_likert.py")


run_feedback()
