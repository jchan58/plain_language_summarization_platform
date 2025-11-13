
import streamlit as st
from pymongo import MongoClient
import datetime

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
                "last_completed_abstract", "feedback", "survey_context",
                "progress_info", "messages", "show_summary",
                "generated_summary", "question_count"
            ]:
                st.session_state.pop(key, None)
            st.switch_page("app.py")

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
    st.write(abs_item["abstract"])

    st.markdown("### Key Terms")
    updated_terms = []
    for idx, term_item in enumerate(abs_item['terms']):
        term = term_item["term"]
        st.write(f"**{term}**")

        familiar = st.radio(
            f"Are you familiar with '{term}'?",
            ["Yes", "No"],
            key=f"fam_{abstract_id}_{idx}"
        )

        extra_info = None
        if familiar == "No":
            extra_info = st.selectbox(
                f"What extra information do you need for '{term}'?",
                ["Definition", "Example", "Background"],
                key=f"extra_{abstract_id}_{idx}"
            )

        updated_terms.append({
            "term": term,
            "familiar": (familiar == "Yes"),
            "extra_information": extra_info
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


