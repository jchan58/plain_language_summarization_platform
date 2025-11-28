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


@st.dialog("Are you sure you want to log out?", dismissible=True)
def logout_confirm_dialog(prolific_id):

    st.markdown("""
    Please logout **only after you have submitted the results for Comparing SUMMARY to ABSTRACT** to make sure your results are saved correctly.
    Otherwise you would have to start back over on the same abstract. 
    """)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Stay on page"):
            st.session_state.show_logout_dialog = False
            st.rerun()

    with col2:
        if st.button("Logout"):
            st.session_state.show_logout_dialog = False
            users_collection.update_one(
                {"prolific_id": prolific_id},
                {"$set": {
                    "phases.interactive.last_completed_index":
                        st.session_state.get("abstract_index", 0)
                }},
                upsert=True
            )

            st.session_state.logged_in = False
            st.session_state.prolific_id = None
            st.switch_page("app.py")

def run_likert():
    data = st.session_state.survey_context
    prolific_id = data["prolific_id"]
    abstract_id = data["abstract_id"]
    abstract = data["abstract"]
    pls = data["pls"]
    if "likert_start_time" not in st.session_state:
        st.session_state.likert_start_time = datetime.utcnow()
    with st.sidebar:
        st.write(f"**MTurk ID:** `{prolific_id}`")
        if st.button("Logout"):
            st.session_state.show_logout_dialog = True
        if st.session_state.get("show_logout_dialog", False):
            st.session_state.show_logout_dialog = False 
            logout_confirm_dialog(prolific_id)

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
        all_answered = all(
            st.session_state.get(k) is not None for k in
            ["simplicity", "coherence", "informativeness", "background", "faithfulness"]
        )

        # Navigation row under Likert questions
        col_back, col_sp1, col_sp2, col_sp3, col_sp4, col_submit = st.columns([1,1,1,1,1,1])
        with col_back:
            if st.button("⬅️ Back", key="likert_back_btn"):
                st.switch_page("pages/static_short_answer.py")
        with col_submit:
            if st.button("Next Abstract", disabled=not all_answered):
                st.session_state.show_next_dialog = True
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
            st.session_state.pop("likert_start_time", None)
            user = users_collection.find_one(
                {"prolific_id": prolific_id},
                {"phases.static.abstracts": 1, "_id": 0}
            )
            abstracts = user["phases"]["static"]["abstracts"]
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
