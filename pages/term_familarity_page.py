import streamlit as st
from pymongo import MongoClient
import re 

TERM_COLORS = [
    "#fffa8b",  # yellow
    "#b3e5fc",  # light blue
    "#c8e6c9",  # light green
    "#ffe0b2",  # light orange
    "#f8bbd0",  # light pink
    "#d1c4e9",  # lavender
    "#f0f4c3",  # pale lime
    "#ffccbc",  # peach
    "#dcedc8",  # mint
    "#e1bee7"   # purple-pink
]

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

    for idx, term_item in enumerate(terms):
        term = term_item["term"]
        color = TERM_COLORS[idx % len(TERM_COLORS)] 
        pattern = re.escape(term)
        highlighted = re.sub(
            fr"\b({pattern})\b",
            rf'<span style="background-color: {color}; padding: 2px 4px; border-radius: 4px;">\1</span>',
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
    
    if "abstract_font_size" not in st.session_state:
        st.session_state.abstract_font_size = 16
    
    if "stage_static" not in st.session_state:
        st.session_state.stage_static = "familiarity"

    st.title("Term Familiarity")

    abstracts = get_user_static_abstracts(prolific_id)
    if "static_index" not in st.session_state: 
        st.session_state.static_index = 0

    if st.session_state.static_index >= len(abstracts):
        st.session_state.static_index = 0

    abs_item = abstracts[st.session_state.static_index]
    abstract_id = abs_item['abstract_id']
    current_num = st.session_state.static_index + 1
    total_num = len(abstracts)

    st.progress(current_num / total_num)
    st.markdown(f"**Progress:** {current_num} / {total_num} abstracts**")
    st.markdown("""
    <style>
    .sticky-abs {
        position: sticky;
        top: 0;
        z-index: 50;
        padding-bottom: 8px;
        background: white;
    }
    </style>
    """, unsafe_allow_html=True)

    # Instructions
    st.markdown("""
    ### 📝 Instructions
    In this task, you will read a scientific abstract and review **10 highlighted terms** extracted from the text.  
    For each term:
    1. Rate your **familiarity** using the slider (1–5).  
    2. Select any **additional information** you would want (definition, example, background, or none).  
    ---
    """)
    st.markdown(f"### ABSTRACT")
    btn_col1, btn_col2, btn_col3 = st.columns([0.25, 0.65, 0.10])
    with btn_col1:
        if st.button("Decrease text size"):
            st.session_state.abstract_font_size = max(12, st.session_state.abstract_font_size - 2)
            st.rerun()

    with btn_col2:
        st.write("")

    with btn_col3:
        if st.button("Increase text size"):
            st.session_state.abstract_font_size = min(30, st.session_state.abstract_font_size + 2)
            st.rerun()
    st.markdown(
        f"""
        <div class="sticky-abs">
            <div style="
                background-color:#f8f9fa;
                padding: 1.1rem 1.3rem;
                border-radius: 0.6rem;
                border: 1px solid #dfe1e5;
                max-height: 550px;
                font-size: {st.session_state.abstract_font_size}px;
                overflow-y: auto;
            ">
                <div style="font-size:{st.session_state.abstract_font_size + 4}px; font-weight: 600; margin-bottom: 0.6rem;">
                    {abs_item['abstract_title']}
                </div>
                <div style="font-size:{st.session_state.abstract_font_size + 4}px; line-height: 1.55;">
                    {highlight_terms_in_abstract(abs_item["abstract"], abs_item["terms"]).replace("\n", "<br>")}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.session_state.stage_static == "familiarity":
        st.subheader("How familiar are you with each term?")
        st.markdown("""
        **Familiarity Scale**  
        1 = Not familiar  
        2 = Somewhat unfamiliar  
        3 = Moderately familiar  
        4 = Familiar  
        5 = Extremely familiar  
        """)

        updated_terms = []

        for idx, term_item in enumerate(abs_item["terms"]):
            term = term_item["term"]

            familiarity = st.slider(
                label=f"{idx+1}. {term}",
                min_value=1,
                max_value=5,
                value=3,
                step=1,
                key=f"fam_{abstract_id}_{idx}"
            )

            updated_terms.append({
                "term": term,
                "familiarity_score": familiarity,
                "extra_information": []
            })

        st.markdown("---")
        all_fam_filled = all(
            st.session_state.get(f"fam_{abstract_id}_{idx}") is not None
            for idx in range(len(abs_item["terms"]))
        )

        if st.button("Next") and all_fam_filled:
            st.session_state.stage_static = "extra_info"
            st.session_state.updated_terms_tmp = updated_terms
            st.rerun()

        if not all_fam_filled:
            st.warning("⚠️ Please answer all familiarity questions before continuing.")

      if st.session_state.stage_static == "extra_info":
        st.subheader("What additional information would you like for each term?")

        # --------------------------------------------------
        # Initialize table only once
        # --------------------------------------------------
        terms = [t["term"] for t in abs_item["terms"]]

        if "extra_table" not in st.session_state:
            st.session_state.extra_table = [
                {"Term": t, "Extra Information": []}
                for t in terms
            ]

        # --------------------------------------------------
        # Render editor
        # --------------------------------------------------
        edited_extra = st.data_editor(
            st.session_state.extra_table,
            key="extra_editor",
            hide_index=True,
            column_config={
                "Extra Information": st.column_config.MultiselectColumn(
                    label="Additional Information Needed",
                    options=["Definition", "Example", "Background", "None"],
                )
            },
            use_container_width=True,
        )

        # --------------------------------------------------
        # Apply "None" logic BEFORE updating session state
        # --------------------------------------------------
        cleaned_extra = []
        for row in edited_extra:
            selections = row["Extra Information"]

            # If "None" is chosen, strip all other selections
            if "None" in selections:
                selections = ["None"]

            cleaned_extra.append({
                "Term": row["Term"],
                "Extra Information": selections
            })

        # Save cleaned version so table updates correctly on next rerun
        st.session_state.extra_table = cleaned_extra

        # --------------------------------------------------
        # Validation check
        # --------------------------------------------------
        all_filled = all(len(row["Extra Information"]) > 0 for row in cleaned_extra)
        if not all_filled:
            st.warning("⚠️ Please select at least one option for each term.")

        # --------------------------------------------------
        # NEXT BUTTON
        # --------------------------------------------------
        if st.button("Next", disabled=not all_filled):
            final_terms = st.session_state.updated_terms_tmp

            # Merge familiarity + extra_info
            for i, row in enumerate(cleaned_extra):
                final_terms[i]["extra_information"] = row["Extra Information"]

            users_collection.update_one(
                {"prolific_id": prolific_id},
                {"$set": {
                    f"phases.static.abstracts.{abstract_id}.term_familarity": final_terms
                }},
            )

            # Reset state
            st.session_state.current_abstract_id = abstract_id
            st.session_state.human_written_pls = abs_item["human_written_pls"]
            st.session_state.stage_static = "familiarity"

            st.switch_page("static_summary")