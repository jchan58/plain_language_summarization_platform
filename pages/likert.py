import streamlit as st
from pymongo import MongoClient
from datetime import datetime
import time
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

@st.dialog("Are you sure you want move onto the next abstract?", dismissible=True)
def confirm_next_abstract():
    st.markdown("You will **not** be able to come back to this abstract if you click **Yes**.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("No"):
            st.session_state.show_next_dialog = False
            st.rerun()

    with col2:
        if st.button("Yes"):
            st.session_state.user_confirmed_next = True
            st.session_state.show_next_dialog = False
            st.rerun()


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

def run_likert():
    data = st.session_state.survey_context
    prolific_id = data["prolific_id"]
    abstract_id = data["abstract_id"]
    abstract = data["abstract"]
    batch_id = data["batch_id"]
    full_type = data["full_type"]
    summary_scale = [
        "1 — Very Poor",
        "2 — Poor",
        "3 — Fair",
        "4 — Good",
        "5 — Excellent"
    ]

    def summary_radio(label, key):
        return st.radio(
            label,
            summary_scale,
            horizontal=True,
            key=key,
            index=None
        )

    chatbot_scale = [
        "1 — Not helpful at all",
        "2 — Slightly helpful",
        "3 — Moderately helpful",
        "4 — Very helpful",
        "5 — Extremely helpful"
    ]

    def chatbot_radio(label, key):
        return st.radio(
            label,
            chatbot_scale,
            horizontal=True,
            key=key,
            index=None
        )
    pls = data["pls"]
    if "likert_saved" in st.session_state:
        for k, v in st.session_state.likert_saved.items():
            if v is not None:
                st.session_state[k] = v
        del st.session_state["likert_saved"]
    if "likert_start_time" not in st.session_state:
        st.session_state.likert_start_time = datetime.utcnow()
    with st.sidebar:
        st.write(f"**MTurk ID:** `{prolific_id}`")
        if st.button("Logout"):
            st.session_state.show_logout_dialog = True
        if st.session_state.get("show_logout_dialog", False):
            st.session_state.show_logout_dialog = False 
            logout_confirm_dialog(prolific_id)

    st.title("Compare AI-Generated SUMMARY to ABSTRACT")
    current = st.session_state.progress_info["current"]
    total = st.session_state.progress_info["total"]
    progress_ratio = current / total if total > 0 else 0
    st.progress(progress_ratio)
    st.caption(f"Completed {current} of {total} abstracts")
    with st.expander("📝 Instructions", expanded=True):
        # st.markdown(
        # """
        # ### 📝 Instructions
        # 1. Read the **ABSTRACT** on the left and the **AI-Generated SUMMARY** on the right.  
        # 2. Answer the comparison questions below to assess how the **AI-Generated SUMMARY** compares to the **ABSTRACT** in terms of clarity, organization, coverage of information, inclusion of background information, and trustworthiness, along with a few questions about your experience using the AI chatbot in this study.
        # 3. When you have finished answering all questions, click the **Next Abstract** button.  
        # 4. In the confirmation popup, verify that you are ready to move on — once you proceed, you **will not** be able to return to this abstract.  

        # **Note:** You may use the **Back** button if you need to revisit the select all that apply questions you had completed for this abstract.
        # """
        # )
        st.markdown(
        """
        ### 📝 Instructions

        **1.** Read the **ABSTRACT** on the left and the **AI-Generated SUMMARY** on the right.\n
        **2.** Answer the questions below, which are organized into three parts:

        &nbsp;&nbsp;**a. Comparing the AI-Generated SUMMARY to the ABSTRACT**  
        &nbsp;&nbsp;Compare the AI-Generated SUMMARY to the ABSTRACT you just read. Rate how well the SUMMARY reflects the ABSTRACT in terms of clarity, organization, coverage of information, inclusion of background information, and trustworthiness.

        &nbsp;&nbsp;**b. Thinking Only About the AI-Generated SUMMARY**  
        &nbsp;&nbsp;Focus only on the AI-Generated SUMMARY, without comparing it to the ABSTRACT. Base your answers on your own understanding, information needs, and perspective.

        &nbsp;&nbsp;**c. Your Experience Using the AI Chatbot**  
        &nbsp;&nbsp;Think about your experience using the AI chatbot during this study. Rate how helpful the chatbot was in answering your questions and supporting your understanding of the ABSTRACT.

        **3.** When you have finished answering all questions, click the **Next Phase** button.  
        You will be asked to confirm before moving on. Once you proceed, you **will not** be able to return to this abstract.

        ---

        **Note:** You may use the **Back** button if you need to revisit the Select All That Apply (SATA) questions you completed for this abstract.
        """
        )

    if "survey_context" not in st.session_state:
        st.warning("Please complete the interactive session first.")
        st.stop()
    
    if "abstract_font_size" not in st.session_state:
        st.session_state.abstract_font_size = 16
    
    if "summary_font_size" not in st.session_state:
        st.session_state.summary_font_size = 16

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
    with col1:
        st.markdown(f"### ABSTRACT")
        btn1, btn2, btn3 = st.columns([0.25, 0.65, 0.10])

        with btn1:
            if st.button("A-", key="abs_decrease"):
                st.session_state.abstract_font_size = max(12, st.session_state.abstract_font_size - 2)
                st.rerun()

        with btn2:
            st.write("")

        with btn3:
            if st.button("A+", key="abs_increase"):
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
        st.markdown("### AI-Generated SUMMARY")
        btn1, btn2, btn3 = st.columns([0.25, 0.65, 0.10])

        with btn1:
            if st.button("A-", key="sum_decrease"):
                st.session_state.summary_font_size = max(12, st.session_state.summary_font_size - 2)
                st.rerun()

        with btn2:
            st.write("")

        with btn3:
            if st.button("A+", key="sum_increase"):
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

    required_keys = [
        "simplicity", "coherence", "informativeness",
        "background", "faithfulness",
        "understanding", "explanation", "importance", "tailored",
        "chatbot_useful", "chatbot_understanding"
    ]

    all_answered = all(
        st.session_state.get(k) is not None for k in required_keys
    )

    spacer_left, main, spacer_right = st.columns([0.25, 1, 0.25])
    with main:
        st.markdown("""
        ### Rating Scale  
        **1 = Very Poor**  
        **2 = Poor**  
        **3 = Fair**  
        **4 = Good**  
        **5 = Excellent**  
        """)

        st.markdown("### Comparing the SUMMARY to the ABSTRACT")
        st.caption("For the following questions, compare the SUMMARY to the ABSTRACT.")

        q1 = summary_radio(
            "How easy was the AI-Generated SUMMARY to understand?",
            "simplicity"
        )
        q2 = summary_radio(
            "How well-structured and logically organized was the AI-Generated SUMMARY?",
            "coherence"
        )
        q3 = summary_radio(
            "How well did the AI-Generated SUMMARY capture the abstract’s main ideas?",
            "informativeness"
        )
        q4 = summary_radio(
            "Was necessary background information included in the AI-Generated SUMMARY?",
            "background"
        )
        q5 = summary_radio(
            "How much do you trust the AI-Generated SUMMARY?",
            "faithfulness"
        )

        st.divider()

        st.markdown("### Thinking Only About the SUMMARY")
        st.caption(
            "For the following questions, consider only the SUMMARY."
        )

        q8 = summary_radio(
            "How well did this AI-Generated SUMMARY match your level of understanding?",
            "understanding"
        )
        q9 = summary_radio(
            "How well did this AI-Generated SUMMARY explain the information you were unfamiliar with?",
            "explanation"
        )
        q10 = summary_radio(
            "How well did this AI-Generated SUMMARY focus on the aspects that mattered most to you?",
            "importance"
        )
        q11 = summary_radio(
            "How well did this AI-Generated SUMMARY feel tailored to you?",
            "tailored"
        )

        st.divider()

        st.markdown("### c. Your Experience Using the AI Chatbot")
        st.markdown("""
        **Rating Scale**  
        **1 = Not helpful at all**  
        **2 = Slightly helpful**  
        **3 = Moderately helpful**  
        **4 = Very helpful**  
        **5 = Extremely helpful**  
        """)

        q6 = chatbot_radio(
            "How useful was the chatbot in answering all your questions?",
            "chatbot_useful"
        )
        q7 = chatbot_radio(
            "How much did the chatbot help you better understand the ABSTRACT?",
            "chatbot_understanding"
        )
        col_back, col_sp1, col_sp2, col_sp3, col_sp4, col_submit = st.columns([1,1,1,1,1,1])
        with col_back:
            if st.button("⬅️ Back", key="likert_back_btn"):
                st.session_state.likert_saved = {
                    "simplicity": st.session_state.get("simplicity"),
                    "coherence": st.session_state.get("coherence"),
                    "informativeness": st.session_state.get("informativeness"),
                    "background": st.session_state.get("background"),
                    "faithfulness": st.session_state.get("faithfulness"),
                    "chatbot_useful": st.session_state.get("chatbot_useful"),
                    "chatbot_understanding": st.session_state.get("chatbot_understanding"), 
                    "understanding": st.session_state.get("understanding"),
                    "explanation": st.session_state.get("explanation"),
                    "importance": st.session_state.get("importance"),
                    "tailored": st.session_state.get("tailored")
                }
                st.switch_page("pages/short_answers.py")

        with col_submit:
            if st.button("Done"):
            # if st.button("Next Batch"):
                if not all_answered:
                    st.warning("Please answer all questions before moving on.")
                else:
                    st.session_state.show_next_dialog = True
            # if st.button("Next Abstract", disabled=not all_answered):
                # st.session_state.show_next_dialog = True
        if st.session_state.get("show_next_dialog", False):
            confirm_next_abstract()
        if st.session_state.get("user_confirmed_next", False):
            st.session_state.user_confirmed_next = False
            likert_time_spent = (datetime.utcnow() - st.session_state.likert_start_time).total_seconds()
            responses = {
                "timestamp": datetime.utcnow(),
                "time_spent_seconds": likert_time_spent,
                "responses": {
                    "simplicity": q1,
                    "coherence": q2,
                    "informativeness": q3,
                    "background_information": q4,
                    "faithfulness": q5, 
                    "chatbot_useful":q6, 
                    "chatbot_understanding":q7,
                    "understanding": q8,
                    "explanation": q9,
                    "importance": q10,
                    "tailored": q11
                }
            }
            users_collection.update_one(
                {"prolific_id": prolific_id},
                {
                    "$set": {
                        f"phases.interactive.batches.{batch_id}.abstracts.{abstract_id}.likert": responses,
                        f"phases.interactive.batches.{batch_id}.abstracts.{abstract_id}.likert_submitted": True,
                        f"phases.interactive.batches.{batch_id}.abstracts.{abstract_id}.completed": True
                    }
                }
            )
            st.session_state.pop("likert_start_time", None)

            # Get user's abstracts for the *current batch*
            user = users_collection.find_one(
                {"prolific_id": prolific_id},
                {f"phases.interactive.batches.{batch_id}.abstracts": 1, "_id": 0}
            )
            abstracts = user["phases"]["interactive"]["batches"][batch_id]["abstracts"]
            next_abstract = None
            for aid in sorted(abstracts.keys(), key=lambda x: int(x)):
                if not abstracts[aid].get("completed", False):
                    next_abstract = {
                        "abstract_id": aid,
                        "abstract": abstracts[aid].get("abstract", ""),
                        "abstract_title": abstracts[aid].get("abstract_title", "")
                    }
                    break

            if next_abstract is None:
                users_collection.update_one(
                    {"prolific_id": prolific_id},
                    {"$set": {f"phases.interactive.batches.{batch_id}.completed": True}}
                )
                st.session_state.next_interactive_abstract = None
                st.switch_page("pages/completed_phase.py")
                return

            # Otherwise, move on to next abstract
            st.session_state.next_interactive_abstract = {
                "abstract": next_abstract["abstract"],
                "abstract_id": next_abstract["abstract_id"],
                "abstract_title": next_abstract["abstract_title"],
                "batch_id": batch_id,
                "full_type": full_type
            }
            for k in [
                "last_completed_abstract",
                "messages",
                "question_count",
                "generated_summary",
                "show_summary",
            ]:
                st.session_state.pop(k, None)

            users_collection.update_one(
                {"prolific_id": prolific_id},
                {"$set": {
                    "last_page": "likert",
                    "last_batch": batch_id,
                    "last_abs_id": abstract_id,
                    "last_full_type": full_type
                }}
            )
            st.switch_page("pages/chatbot.py")
           
run_likert()
