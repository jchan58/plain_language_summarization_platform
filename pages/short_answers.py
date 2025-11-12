import streamlit as st
from pymongo import MongoClient
from datetime import datetime

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
        st.title("Session Controls")
        if "last_completed_abstract" in st.session_state:
            user_info = st.session_state.last_completed_abstract
            st.markdown(f"**MTurk ID:** `{user_info['prolific_id']}`")

        if st.button("Logout"):
            for key in [
                "last_completed_abstract", "feedback", "survey_context",
                "progress_info", "messages", "show_summary",
                "generated_summary", "question_count"
            ]:
                st.session_state.pop(key, None)
            st.switch_page("app.py")
    show_progress()
    st.markdown(
        """
        ### 📝 Instructions
        1. Read the summary shown below. The summary is another version of the abstract.  
        2. Answer the short answer questions to check your understanding.  
        3. **DO NOT copy** from the summary, say “I don’t know,” or provide unrelated answers.  
           Please respond to the questions to the best of your ability — doing otherwise may risk not being compensated for the task.  
        4. When you have finished answering all questions, click the **Next** button to continue.  
        """
    )

    # Check that interactive portion is completed
    if "last_completed_abstract" not in st.session_state:
        st.warning("Please complete the interactive session first.")
        st.stop()

    data = st.session_state.last_completed_abstract
    prolific_id = data["prolific_id"]
    abstract_id = data["abstract_id"]

    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.title("Summary of Scientific Abstract")
        st.markdown(f"### {data['title']}")
        st.markdown(
            f"""
            <div class="no-select" style="
                background-color:#f2f3f5;
                padding:1rem;
                border-radius:0.5rem;
                line-height:1.6;
                border:1px solid #dcdcdc;
                margin-bottom:1rem;">
                {data["pls"]}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.title("Summary of Scientific Abstract")
        if "feedback" not in st.session_state:
            st.session_state.feedback = {"main_idea": "", "method": "", "result": ""}

        def update_main_idea():
            st.session_state.feedback["main_idea"] = st.session_state.main_idea_box

        def update_method():
            st.session_state.feedback["method"] = st.session_state.method_box

        def update_result():
            st.session_state.feedback["result"] = st.session_state.result_box

        st.markdown("### 🧠 What did the researchers in this study want to find out?")
        st.text_area("", key="main_idea_box", value=st.session_state.feedback["main_idea"], on_change=update_main_idea)

        st.markdown("### 🧪 What was the method used in the study?")
        st.text_area("", key="method_box", value=st.session_state.feedback["method"], on_change=update_method)

        st.markdown("### 📊 What was the result of this study?")
        st.text_area("", key="result_box", value=st.session_state.feedback["result"], on_change=update_result)

        all_filled = all([
            st.session_state.feedback["main_idea"].strip(),
            st.session_state.feedback["method"].strip(),
            st.session_state.feedback["result"].strip()
        ])

        if st.button("Next", disabled=not all_filled):
            feedback_data = {
                "main_idea": st.session_state.feedback["main_idea"].strip(),
                "methods": st.session_state.feedback["method"].strip(),
                "results": st.session_state.feedback["result"].strip(),
                "submitted_at": datetime.utcnow()
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
                "abstract_id": abstract_id
            }

            st.switch_page("pages/likert.py")

run_feedback()
