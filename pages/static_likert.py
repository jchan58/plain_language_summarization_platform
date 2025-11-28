import streamlit as st
from pymongo import MongoClient
from datetime import datetime
import sys
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

def run_likert():
    with st.sidebar:
        if "last_completed_abstract" in st.session_state:
            user_info = st.session_state.last_completed_abstract
            st.markdown(f"**MTurk ID:** `{user_info['prolific_id']}`")

        if st.button("Logout"):
            for key in [
            "last_completed_abstract",
            "survey_context",
            "feedback",
            "progress_info",
            "messages",
            "show_summary",
            "generated_summary",
            "question_count"
            ]:
                st.session_state.pop(key, None)
            st.switch_page("app.py")

    data = st.session_state.survey_context
    prolific_id = data["prolific_id"]
    abstract_id = data["abstract_id"]
    abstract = data["abstract"]
    pls = data["pls"]

    if "survey_context" not in st.session_state:
        st.warning("Please complete previous task.")
        st.stop()
    
    if "abstract_font_size" not in st.session_state:
        st.session_state.abstract_font_size = 16
    
    if "summary_font_size" not in st.session_state:
        st.session_state.summary_font_size = 16

    st.title("Comparing SUMMARY to ABSTRACT")
    current_index = st.session_state.progress_info["current_index"]
    total = st.session_state.progress_info["total"]
    progress_ratio = current_index / total if total > 0 else 0
    st.progress(progress_ratio)
    st.caption(f"Completed {current_index} of {total} abstracts")
    st.markdown(
        """
        ### 📝 Instructions
        1. Read the scientific abstract and the **SUMMARY** shown below.  
        2. Fill out the survey questions below that compares the **SUMMARY** to the **ABSTRACT**.  
        3. When you have finished answering all questions, click the **Submit** button below.  
        """,
    )

    

    st.markdown("""
        <style>
        div[data-testid="stHorizontalBlock"] {
            align-items: flex-start !important;
        }
        .content-box {
            background-color: #f7f8fa;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 1rem 1.3rem;
            line-height: 1.55;
            font-size: 1.05rem;
        }
        .summary-box {
            background-color: #e8f4ff;      
            border: 1px solid #c6ddf7;      
            border-radius: 10px;
            padding: 1rem 1.3rem;
            line-height: 1.55;
            font-size: 1.05rem;
        }
        h3 {
            margin-top: 0.5rem !important;
            margin-bottom: 0.6rem !important;
        }
        </style>
        """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1], gap="large")
    st.progress(current / total)
    st.markdown(f"**Progress:** {current} / {total} abstracts**")
    with col1:
        st.markdown(f"### ABSTRACT")
        btn1, btn2, btn3 = st.columns([0.25, 0.55, 0.20])

        with btn1:
            if st.button("Decrease text size", key="abs_decrease"):
                st.session_state.abstract_font_size = max(12, st.session_state.abstract_font_size - 2)
                st.rerun()

        with btn2:
            st.write("")

        with btn3:
            if st.button("Increase text size", key="abs_increase"):
                st.session_state.abstract_font_size = min(30, st.session_state.abstract_font_size + 2)
                st.rerun()

        st.markdown(
            f"""
            <div style="
                background-color:#f8f9fa;
                padding: 1.1rem 1.3rem;
                border-radius: 0.6rem;
                border: 1px solid #dfe1e5;
                max-height: 550px;
                overflow-y: auto;
                font-size: {st.session_state.abstract_font_size}px;
                line-height: 1.55;
            ">
                <div style="line-height: 1.55;">
                    {abstract}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


    with col2:
        st.markdown("### SUMMARY")
        btn1, btn2, btn3 = st.columns([0.25, 0.55, 0.20])

        with btn1:
            if st.button("Decrease text size", key="sum_decrease"):
                st.session_state.summary_font_size = max(12, st.session_state.summary_font_size - 2)
                st.rerun()

        with btn2:
            st.write("")

        with btn3:
            if st.button("Increase text size", key="sum_increase"):
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
                    {pls}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.divider()

    spacer_left, main, spacer_right = st.columns([0.25, 1, 0.25])
    with main:
        st.markdown("### Comparing the SUMMARY to the ABSTRACT")
        st.markdown("""
        ### Rating Scale  
        **1 = Very Poor**  
        **2 = Poor**  
        **3 = Fair**  
        **4 = Good**  
        **5 = Excellent**  
        """)

        likert_scale = [1, 2, 3, 4, 5]

        q1 = st.radio("How easy was the SUMMARY to understand?",
                      likert_scale, horizontal=True, key="simplicity")
        q2 = st.radio("How well-structured and logically organized was the SUMMARY?",
                      likert_scale, horizontal=True, key="coherence")
        q3 = st.radio("How well did the SUMMARY capture the abstract’s main ideas?",
                      likert_scale, horizontal=True, key="informativeness")
        q4 = st.radio("Was necessary background information included in the SUMMARY?",
                      likert_scale, horizontal=True, key="background")
        q5 = st.radio("How much do you trust the SUMMARY?",
                      likert_scale, horizontal=True, key="faithfulness")

        client = MongoClient(st.secrets["MONGO_URI"])
        db = client["pls"]
        users_collection = db["users"]

        all_answered = all([
            st.session_state.get("simplicity"),
            st.session_state.get("coherence"),
            st.session_state.get("informativeness"),
            st.session_state.get("background"),
            st.session_state.get("faithfulness")
        ])

        submit_button = st.button("Submit", disabled=not all_answered)
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

            users_collection.update_one(
                {"prolific_id": prolific_id},
                {
                    "$set": {
                        f"phases.static.abstracts.{abstract_id}.likert": responses,
                        f"phases.static.abstracts.{abstract_id}.likert_submitted": True,
                        f"phases.static.abstracts.{abstract_id}.completed": True
                    }
                }
            )

            user = users_collection.find_one(
                {"prolific_id": prolific_id},
                {"phases.static.abstracts": 1, "_id": 0}
            )

            abstracts = user["phases"]["static"]["abstracts"]

            # Find next uncompleted static abstract
            next_abstract = None
            for aid in sorted(abstracts.keys(), key=lambda x: int(x)):
                if not abstracts[aid].get("completed", False):
                    next_abstract = {
                        "abstract_id": aid,
                        "abstract": abstracts[aid].get("abstract", ""),
                        "abstract_title": abstracts[aid].get("abstract_title", "")
                    }
                    break

            # If NO more abstracts → mark static phase complete
            if next_abstract is None:
                users_collection.update_one(
                    {"prolific_id": prolific_id},
                    {"$set": {"phases.static.completed": True}}
                )

                st.session_state.next_static_abstract = None
                st.switch_page("pages/completed.py")
                return

            # Otherwise → save next abstract and move forward
            st.session_state.next_static_abstract = {
                "abstract": next_abstract["abstract"],
                "abstract_id": next_abstract["abstract_id"],
                "abstract_title": next_abstract["abstract_title"]
            }

            # Clear old data from last abstract
            for k in [
                "survey_context",
                "last_completed_abstract",
                "messages",
                "question_count",
                "generated_summary",
                "show_summary",
            ]:
                st.session_state.pop(k, None)

            st.switch_page("pages/term_familarity_page.py")

            

run_likert()
