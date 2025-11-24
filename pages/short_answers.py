import streamlit as st
from pymongo import MongoClient
from datetime import datetime

# define minium character count 
MIN_CHARS = 75
st.markdown("""
<script>
function attachLiveCounter(wrapperId, counterId) {
    const wrapper = parent.document.getElementById(wrapperId);
    if (!wrapper) return;

    const ta = wrapper.querySelector("textarea");
    const counter = parent.document.getElementById(counterId);

    if (ta && counter) {
        ta.addEventListener("input", () => {
            counter.innerHTML = ta.value.length + " characters";
        });
    }
}
</script>
""", unsafe_allow_html=True)
st.markdown(
    """
    <style>
        [data-testid="stSidebarNav"] {display: none;}
    </style>
    """,
    unsafe_allow_html=True
)

st.set_page_config(layout="wide")
def text_area_with_counter(label, key_name, state_key):
    st.subheader(label)
    wrapper_id = f"{key_name}_wrapper"
    counter_id = f"{key_name}_count"
    st.markdown(f"<div id='{wrapper_id}'>", unsafe_allow_html=True)
    st.text_area("", key=key_name, value=st.session_state.feedback[state_key])
    st.markdown("</div>", unsafe_allow_html=True)
    st.caption(
        f"<span id='{counter_id}'>{len(st.session_state.feedback[state_key])} characters</span>",
        unsafe_allow_html=True
    )
    st.markdown(
        f"<script>attachLiveCounter('{wrapper_id}', '{counter_id}');</script>",
        unsafe_allow_html=True
    )
    st.session_state.feedback[state_key] = st.session_state[key_name]

def show_progress():
    if "progress_info" in st.session_state:
        progress = st.session_state.progress_info
        current = progress.get("current_index", 0)
        total = progress.get("total", 1)
        st.progress(current / total)
        st.caption(f"Progress: {current} of {total} abstracts completed")

def run_feedback():
    with st.sidebar:
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
        1. Please read the summary shown below, which was generated from the previous page.
        2. Answer the short answer questions to check your understanding.  
        3. **DO NOT copy** from the summary, say “I don’t know,” or provide unrelated answers.  
           Please respond to the questions to the best of your ability — doing otherwise may risk not being compensated for the task.  
        4. When you have finished answering all questions, click the **Next** button to continue.  
        """
    )

    if "last_completed_abstract" not in st.session_state:
        st.warning("Please complete the interactive session first.")
        st.stop()

    data = st.session_state.last_completed_abstract
    prolific_id = data["prolific_id"]
    abstract_id = data["abstract_id"]
    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.title("SUMMARY")
        st.markdown(
        f"""
        <div style="
            background-color:#e8f4ff;
            padding: 1.1rem 1.3rem;
            border-radius: 0.6rem;
            border: 1px solid #dfe1e5;
            max-height: 550px;
            overflow-y: auto;
        ">
            <div style="font-size: 1.15rem; font-weight: 600; margin-bottom: 0.6rem;">
                {data['title']}
            </div>
            <div style="font-size: 1rem; line-height: 1.55;">
                {data['pls']}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    with col2:
        st.title("Short Answer Questions")
        if "feedback" not in st.session_state:
            st.session_state.feedback = {"main_idea": "", "method": "", "result": ""}

        def update_main_idea():
            st.session_state.feedback["main_idea"] = st.session_state.main_idea_box

        def update_method():
            st.session_state.feedback["method"] = st.session_state.method_box

        def update_result():
            st.session_state.feedback["result"] = st.session_state.result_box

        st.markdown("""
        <style>
        div[data-testid="stMarkdownContainer"] h3 {
            margin-bottom: 0.2rem !important;
            margin-top: 0.8rem !important;
        }
        textarea {
            margin-top: -0.3rem !important;
        }
        </style>
        """, unsafe_allow_html=True)

        text_area_with_counter("🧠 What did the researchers in this study want to find out?",
                       "main_idea_box", "main_idea")

        text_area_with_counter("🧪 What was the method used in the study?",
                            "method_box", "method")

        text_area_with_counter("📊 What was the result of this study?",
                            "result_box", "result")


        all_filled = all([
            len(st.session_state.feedback["main_idea"].strip()) >= MIN_CHARS,
            len(st.session_state.feedback["method"].strip()) >= MIN_CHARS,
            len(st.session_state.feedback["result"].strip()) >= MIN_CHARS
        ])

        if not all_filled:
            st.warning(
                f"❗Each response must be at least {MIN_CHARS} characters long. Please expand your answer(s)."
            )

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
