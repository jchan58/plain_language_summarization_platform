import streamlit as st
from pymongo import MongoClient
from datetime import datetime

def run_likert():
    st.markdown(
    """
    ### 📝 Instructions
    1. Read the scientific abstract and the **summary** shown below.  
    2. Fill out the survey questions about the **summary**.  
    3. When you have finished answering all questions, click the **Next** button to continue.  
    """
    )
    st.title("📝 Scientific Abstract")

    if "survey_context" not in st.session_state:
        st.warning("Please complete the interactive session first.")
        st.stop()
    
    data = st.session_state.survey_context
    prolific_id = data["prolific_id"]
    abstract_id = data["abstract_id"]
    abstract = data["abstract"]
    pls = data["pls"]
    abstract_title = data["abstract_title"]

    st.markdown(f"### {abstract_title}")
    st.markdown(abstract)

    st.markdown("### Summary of Scientific Abstract")
    st.markdown(pls)
    
    st.divider()
    st.markdown("### 📊 Likert-Scale Evaluation (1–5)")
    st.caption("1 = Very Poor  5 = Excellent")

    likert_scale = [1, 2, 3, 4, 5]

    # likert scale questions
    q1 = st.radio("🧠 **Simplicity:** How easy was the summary to understand?",
                  likert_scale, horizontal=True, key="simplicity")
    q2 = st.radio("How well-structured and logically organized was the summary?",
                  likert_scale, horizontal=True, key="coherence")
    q3 = st.radio("How well did the PLS capture the abstract’s content?",
                  likert_scale, horizontal=True, key="informativeness")
    q4 = st.radio("Was necessary background information included?",
                  likert_scale, horizontal=True, key="background")
    q5 = st.radio("How accurately did the summary reflect the original abstract?",
                  likert_scale, horizontal=True, key="faithfulness")

    # MongoDB connection
    client = MongoClient(st.secrets["MONGO_URI"])
    db = client["pls"]
    users_collection = db["users"]

    # Check if all answers are selected
    all_answered = all([
        st.session_state.get("simplicity"),
        st.session_state.get("coherence"),
        st.session_state.get("informativeness"),
        st.session_state.get("background"),
        st.session_state.get("faithfulness")
    ])

    # disable submit button until all questions are answered
    submit_button = st.button("Submit Responses", disabled=not all_answered)

    if submit_button:
        responses = {
            "timestamp": datetime.utcnow(),
            "responses": {
                "simplicity": q1,
                "coherence": q2,
                "informativeness": q3,
                "background_information": q4,
                "faithfulness": q5
            }
        }

        result = users_collection.update_one(
            {"prolific_id": prolific_id},
            {
                "$set": {
                    f"phases.interactive.abstracts.{abstract_id}.likert": responses,
                    f"phases.interactive.abstracts.{abstract_id}.likert_submitted": True
                }
            }
        )

        if result.modified_count > 0:
            st.success("Thank you! Your responses have been recorded.")
        else:
            st.warning("No changes were made. Please check your connection or data.")

run_likert()