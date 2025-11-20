import streamlit as st
from pymongo import MongoClient
import re 

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

db = get_mongo_client()["pls"]
users_collection = db["users"]
abstracts_collection = db["abstracts"]

# highlight the terms in the abstract
def highlight_terms_in_abstract(abstract: str, terms: list):
    highlighted = abstract
    for term_item in terms:
        term = term_item["term"]
        # Escape regex chars
        pattern = re.escape(term)
        highlighted = re.sub(
            fr"\b({pattern})\b",
            r'<span style="background-color: #fffa8b; padding: 2px 4px; border-radius: 4px;">\1</span>',
            highlighted,
            flags=re.IGNORECASE
        )
    return highlighted

@st.dialog("📝 Instructions", width="medium", dismissible=False)
def static_instructions(prolific_id):
    st.markdown("""
    ### Before you begin

    For this task, you will identify your **familiarity level** for each term and indicate whether you need additional information (background, example, and/or definition).
    For this batch, **10 terms** have been extracted from the abstract, and they are highlighted within the text.
    Please follow these steps:

    - For each term, indicate **how familiar** you are with it using the provided scale.
    - If you **want additional information**, specify what type of information you need for each term:
        - **definition**
        - **example**
        - **background information**
    - After completing all 10 terms, click **Next**.
    - On the next page, you will answer **3 questions** about the **SUMMARY** of the abstract you saw on this page.

    ---
    """)
    if st.button("Start"):
        st.session_state.seen_static_instructions = True
        users_collection.update_one(
            {"prolific_id": prolific_id},
            {"$set": {"phases.static.seen_instructions": True}},
            upsert=True
        )
        st.rerun()

# go through the abstracts in the static portion 
def get_user_static_abstracts(prolific_id: str):
    user = users_collection.find_one(
        {"prolific_id": prolific_id},
        {"_id": 0, "phases.static.abstracts": 1}
    )
    if not user:
        return []

    abstracts_dict = user["phases"]["static"]["abstracts"]

    abstracts = []

    for abstract_id, data in abstracts_dict.items():
        if not data.get("completed", False):
            abstracts.append({
                "abstract_id": abstract_id,
                "abstract_title": data.get("abstract_title", ""),
                "abstract": data.get("abstract", ""),
                "human_written_pls": data.get("human_written_pls", ""), 
                "terms": data.get("term_familarity", [])
            })

    abstracts = sorted(abstracts, key=lambda x: int(x["abstract_id"]))
    return abstracts


def run_terms(prolific_id: str): 
    with st.sidebar:
        if "prolific_id" in st.session_state:
            st.markdown(f"**MTurk ID:** `{st.session_state.prolific_id}`")

        if st.button("Logout"):
            for key in [
                "static_index", "current_abstract_id", "human_written_pls",
                "prolific_id", "messages", "feedback", "survey_context",
                "progress_info", "show_summary", "generated_summary",
                "question_count"
            ]:
                st.session_state.pop(key, None)
            st.switch_page("app.py")

    user = users_collection.find_one({"prolific_id": prolific_id})
    db_seen = (
        user.get("phases", {})
            .get("static", {})
            .get("seen_instructions", False)
    )

    if "seen_static_instructions" not in st.session_state:
        st.session_state.seen_static_instructions = db_seen
    if not st.session_state.seen_static_instructions:
        static_instructions(prolific_id)
        return
    st.title("Term Familiarity")
    abstracts = get_user_static_abstracts(prolific_id)

    if "static_index" not in st.session_state: 
        st.session_state.static_index = 0
    
    if st.session_state.static_index >= len(abstracts):
        st.session_state.static_index = 0

    # current abstraction 
    abs_item = abstracts[st.session_state.static_index]
    abstract_id = abs_item['abstract_id']

    st.subheader(abs_item["abstract_title"])
    current_num = st.session_state.static_index + 1
    total_num = len(abstracts)
    st.progress(current_num / total_num)
    st.markdown(f"**Progress:** {current_num} / {total_num} abstracts")
    raw_abstract = abs_item["abstract"]
    highlighted_abstract = highlight_terms_in_abstract(raw_abstract, abs_item["terms"])
    formatted_abstract = highlighted_abstract.replace("\n", "  \n")
    st.markdown(
        f"""
        <div style="
            background-color: #f8f9fa;
            padding: 0.8rem 1rem;        
            border-radius: 0.6rem;
            border: 1px solid #dfe1e5;
            max-height: 550px;
            overflow-y: auto;
            white-space: normal;
        ">
            <div style="
                font-size: 1.08rem;
                line-height: 1.55;
                margin: 0 !important;     
                padding: 0 !important;     
            ">
                {formatted_abstract}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("### Key Terms")
    updated_terms = []

    for idx, term_item in enumerate(abs_item['terms']):
        term = term_item["term"]
        st.write(f"**{idx + 1}. {term}**")
        familiarity = st.slider(
            f"How familiar are you with '{term}'?",
            min_value=1,
            max_value=5,
            value=1,
            format="%d",
            key=f"fam_{abstract_id}_{idx}"
        )

        extra_info = st.multiselect(
            f"What additional information do you need for '{term}' (optional)?",
            ["Definition", "Example", "Background"],
            key=f"extra_{abstract_id}_{idx}"
        )

        updated_terms.append({
            "term": term,
            "familiarity_score": familiarity,      
            "extra_information": extra_info if extra_info else []
        })

    st.markdown("---")

    if st.button("Next"):
        users_collection.update_one(
            {"prolific_id": prolific_id},
            {
                "$set": {
                    f"phases.static.abstracts.{abstract_id}.term_familarity": updated_terms
                }
            }
        )
        st.session_state.current_abstract_id = abstract_id
        st.session_state.human_written_pls = abs_item['human_written_pls']
        st.session_state.prolific_id = prolific_id
        st.switch_page("static_summary")


