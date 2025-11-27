import streamlit as st
from pymongo import MongoClient
import re
import sys

print(">>>> ENTERED CHATBOT PAGE <<<<", file=sys.stderr)
print(">>>> chatbot.py LOADED", file=sys.stderr)
print("prolific_id IN SESSION? ", "prolific_id" in st.session_state, file=sys.stderr)
if "prolific_id" in st.session_state:
    print("VALUE = ", st.session_state.prolific_id, file=sys.stderr)
else:
    print("VALUE = MISSING", file=sys.stderr)
if "next_interactive_abstract" in st.session_state:
    print(">>>> next_static_abstract EXISTS:", 
          st.session_state["next_interactive_abstract"],
          type(st.session_state["next_interactive_abstract"]),
          file=sys.stderr)
else:
    print(">>>> next_interactive_abstract DOES NOT EXIST", file=sys.stderr)

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
    ...
    """)

    if st.button("Start"):
        st.session_state.seen_static_instructions = True
        users_collection.update_one(
            {"prolific_id": prolific_id},
            {"$set": {"phases.static.seen_instructions": True}},
            upsert=True
        )
        st.rerun()


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

    # ---------------- SIDEBAR ---------------- #
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

    # ----------------------------------------- #

    # Instruction check
    user = users_collection.find_one({"prolific_id": prolific_id})
    db_seen = user.get("phases", {}).get("static", {}).get("seen_instructions", False)

    if "seen_static_instructions" not in st.session_state:
        st.session_state.seen_static_instructions = db_seen

    if not st.session_state.seen_static_instructions:
        static_instructions(prolific_id)
        return

    # ----------------------------------------- #

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
    abstract_id = abs_item["abstract_id"]

    current_num = st.session_state.static_index + 1
    total_num = len(abstracts)

    st.progress(current_num / total_num)
    st.markdown(f"**Progress:** {current_num} / {total_num} abstracts**")

    # ABSTRACT HEADER
    st.markdown("""<style>.sticky-abs {position:sticky;top:0;z-index:50;padding-bottom:8px;background:white;}</style>""",
                unsafe_allow_html=True)

    st.markdown("### ABSTRACT")

    btn_col1, btn_col2, btn_col3 = st.columns([0.25, 0.65, 0.10])
    with btn_col1:
        if st.button("Decrease text size"):
            st.session_state.abstract_font_size = max(12, st.session_state.abstract_font_size - 2)
            st.rerun()

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
                <div style="font-size:{st.session_state.abstract_font_size + 4}px; font-weight:600; margin-bottom:0.6rem;">
                    {abs_item['abstract_title']}
                </div>
                <div style="font-size:{st.session_state.abstract_font_size + 4}px; line-height:1.55;">
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
            color = TERM_COLORS[idx % len(TERM_COLORS)]
            col_label, col_slider = st.columns([0.45, 0.55])

            with col_label:
                st.markdown(
                    f"""
                    <div style="
                        background-color:{color};
                        padding:8px 12px;
                        border-radius:6px;
                        font-size:16px;
                        font-weight:600;
                        display:flex;
                        align-items:center;
                        height:42px;
                    ">
                        {idx+1}. {term}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col_slider:
                st.markdown("<div style='margin-top:-10px;'>", unsafe_allow_html=True)
                familiarity = st.slider(
                    label=" ",
                    min_value=1,
                    max_value=5,
                    value=3,
                    step=1,
                    key=f"fam_{abstract_id}_{idx}",
                )
                st.markdown("</div>", unsafe_allow_html=True)

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

        if st.button("Next", key=f"next_btn_fam_{abstract_id}", disabled=not all_fam_filled):
            st.session_state.stage_static = "extra_info"
            st.session_state.updated_terms_tmp = updated_terms
            st.rerun()

        if not all_fam_filled:
            st.warning("⚠️ Please answer all familiarity questions before continuing.")

        return  # IMPORTANT — stops rendering here when on the familiarity page
    
    if st.session_state.stage_static == "extra_info":

        st.subheader("What additional information would you like for each term?")
        st.markdown("Choose at least one option per term, unless you select 'None'.")

        terms = [t["term"] for t in abs_item["terms"]]

        if "extra_info_state" not in st.session_state:
            st.session_state.extra_info_state = {term: [] for term in terms}

        cleaned_extra = []

        for idx, term in enumerate(terms):
            color = TERM_COLORS[idx % len(TERM_COLORS)]

            st.markdown("<div style='height:2px;background-color:#eee;margin:1rem 0;'></div>",
                        unsafe_allow_html=True)

            col_term, col_opts = st.columns([0.35, 0.65])

            with col_term:
                st.markdown(
                    f"""
                    <div style="display:flex;align-items:center;">
                        <div style="
                            width:16px;height:16px;
                            background-color:{color};
                            border-radius:4px;
                            margin-right:10px;
                            border:1px solid #ccc;"></div>
                        <div style="font-size:1.1rem;font-weight:600;">
                            {idx+1}. {term}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col_opts:
                base_key = f"extra_{abstract_id}_{idx}"
                current = st.session_state.extra_info_state.get(term, [])

                none_selected = "None" in current
                disabled_others = none_selected

                def_checked = "Definition" in current
                example_checked = "Example" in current
                bg_checked = "Background" in current

                c1, c2, c3, c4 = st.columns([1, 1, 1, 1])

                with c1:
                    if st.checkbox("Definition", value=def_checked,
                                   key=f"{base_key}_def", disabled=disabled_others):
                        current = [x for x in current if x != "None"]
                        if "Definition" not in current:
                            current.append("Definition")
                    else:
                        current = [x for x in current if x != "Definition"]

                with c2:
                    if st.checkbox("Example", value=example_checked,
                                   key=f"{base_key}_ex", disabled=disabled_others):
                        current = [x for x in current if x != "None"]
                        if "Example" not in current:
                            current.append("Example")
                    else:
                        current = [x for x in current if x != "Example"]

                with c3:
                    if st.checkbox("Background", value=bg_checked,
                                   key=f"{base_key}_bg", disabled=disabled_others):
                        current = [x for x in current if x != "None"]
                        if "Background" not in current:
                            current.append("Background")
                    else:
                        current = [x for x in current if x != "Background"]

                with c4:
                    if st.checkbox("None", value=none_selected,
                                   key=f"{base_key}_none"):
                        current = ["None"]
                    else:
                        current = [x for x in current if x != "None"]

                st.session_state.extra_info_state[term] = current
                cleaned_extra.append({"term": term, "extra_information": current})

        st.markdown("---")

        all_filled = all(len(row["extra_information"]) > 0 for row in cleaned_extra)

        if st.button("Next", key=f"next_extra_{abstract_id}", disabled=not all_filled):

            final_terms = st.session_state.updated_terms_tmp
            for i, row in enumerate(cleaned_extra):
                final_terms[i]["extra_information"] = row["extra_information"]

            users_collection.update_one(
                {"prolific_id": prolific_id},
                {"$set": {f"phases.static.abstracts.{abstract_id}.term_familarity": final_terms}}
            )
            st.session_state.current_abstract_id = abstract_id
            st.session_state.current_abstract = abs_item["abstract"]
            st.session_state.human_written_pls = abs_item["human_written_pls"]
            st.session_state.abstract_title = abs_item["abstract_title"]
            st.session_state.prolific_id = prolific_id

            # RESET for next abstract
            st.session_state.stage_static = "familiarity"
            st.session_state.extra_info_state = {}
            st.switch_page("pages/static_short_answer.py")