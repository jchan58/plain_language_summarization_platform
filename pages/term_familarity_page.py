import streamlit as st
from pymongo import MongoClient
import re
import sys
import datetime
from navigation import render_nav

print(">>>> ENTERED Term PAGE <<<<", file=sys.stderr)
print(">>>> term.py LOADED", file=sys.stderr)
print("prolific_id IN SESSION? ", "prolific_id" in st.session_state, file=sys.stderr)
if "prolific_id" in st.session_state:
    print("VALUE = ", st.session_state.prolific_id, file=sys.stderr)
else:
    print("VALUE = MISSING", file=sys.stderr)
if "next_static_abstract" in st.session_state:
    print(">>>> next_static_abstract EXISTS:", 
          st.session_state["next_static_abstract"],
          type(st.session_state["next_static_abstract"]),
          file=sys.stderr)
else:
    print(">>>> next_static_abstract DOES NOT EXIST", file=sys.stderr)
print("=== SESSION STATE DUMP ===", file=sys.stderr)
for k, v in st.session_state.items():
    print(f"{k}: {v}", file=sys.stderr)
print("===========================", file=sys.stderr)

TERM_COLORS = [
    "#fffa8b", "#b3e5fc", "#c8e6c9", "#ffe0b2", "#f8bbd0",
    "#d1c4e9", "#f0f4c3", "#ffccbc", "#dcedc8", "#e1bee7"
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

# connect to MongoDB
MONGO_URI = st.secrets["MONGO_URI"]
client = MongoClient(MONGO_URI)
db = client["pls"]
users_collection = db["users"]

@st.fragment
def familiarity_fragment(abs_item, abstract_id):
    updated_terms = []

    for idx, term_item in enumerate(abs_item["terms"]):
        term = term_item["term"]
        color = TERM_COLORS[idx % len(TERM_COLORS)]

        # Load previous value if exists
        prev_val = None
        if "updated_terms_tmp" in st.session_state:
            prev_val = st.session_state.updated_terms_tmp[idx]["familiarity_score"]

        col_label, col_slider = st.columns([0.45, 0.55])

        with col_label:
            st.markdown(
                f"""
                <div style="background-color:{color};padding:8px 12px;border-radius:6px;font-size:16px;font-weight:600;
                display:flex;align-items:center;height:42px;">
                    {idx+1}. {term}
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_slider:
            familiarity = st.slider(
                label=" ",
                min_value=1,
                max_value=5,
                value=prev_val if prev_val is not None else 3,
                step=1,
                key=f"fam_{abstract_id}_{idx}",
            )

        updated_terms.append({
            "term": term,
            "familiarity_score": familiarity,
            "extra_information": []
        })

    return updated_terms

@st.fragment
def abstract_fragment(abs_item, font_size):
    st.markdown(
        f"""
        <div class="sticky-abs">
            <div style="background-color:#f8f9fa;padding:1.1rem 1.3rem;border-radius:0.6rem;border:1px solid #dfe1e5;
            max-height:550px;font-size:{font_size}px;overflow-y:auto;">
                <div style="font-size:{font_size + 4}px;font-weight:600;margin-bottom:0.6rem;">
                    {abs_item['abstract_title']}
                </div>
                <div style="font-size:{font_size + 4}px;line-height:1.55;">
                    {abs_item['highlighted_html'].replace("\n","<br>")}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
def familiarity_page(abs_item, abstract_id):
    st.subheader("How familiar are you with each term?")
    st.markdown("""
    **Familiarity Scale**  
    1 = Not familiar  
    2 = Somewhat unfamiliar  
    3 = Moderately familiar  
    4 = Familiar  
    5 = Extremely familiar  
    """)

    # sliders (use your existing fragment inside)
    updated_terms = familiarity_fragment(abs_item, abstract_id)

    st.markdown("---")

    all_fam_filled = all(
        st.session_state.get(f"fam_{abstract_id}_{idx}") is not None
        for idx in range(len(abs_item["terms"]))
    )

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col6:
        next_clicked = st.button(
            "Next ➡️",
            key=f"next_btn_fam_{abstract_id}",
            disabled=not all_fam_filled
        )

    return updated_terms, next_clicked, all_fam_filled

@st.cache_data
def cached_highlight(abstract, terms):
    return highlight_terms_in_abstract(abstract, terms)

def load_user(prolific_id, projection=None):
    return users_collection.find_one(
        {"prolific_id": prolific_id},
        projection
    )

def load_user_info(prolific_id):
    return users_collection.find_one({"prolific_id": prolific_id})

@st.dialog("Are you sure you want to log out?", dismissible=False)
def logout_confirm_dialog(prolific_id):
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

def get_static_progress(prolific_id, batch_id):
    user = load_user(
        prolific_id,
        {f"phases.static.batches.{batch_id}.abstracts": 1, "_id": 0}
    )
    if not user:
        return 0, 0

    abstracts = (
        user["phases"]["static"]["batches"][batch_id]["abstracts"]
    )
    total = len(abstracts)
    completed = sum(1 for a in abstracts.values() if a.get("completed", False))
    return completed, total

def highlight_terms_in_abstract(abstract: str, terms: list):
    highlighted = abstract
    for idx, term_item in enumerate(terms):
        term = term_item["term"]
        color = TERM_COLORS[idx % len(TERM_COLORS)]
        pattern = re.escape(term)
        highlighted = re.sub(
            fr"\b({pattern})\b",
            rf'<span style="background-color:{color}; padding:2px 4px; border-radius:4px;">\1</span>',
            highlighted,
            flags=re.IGNORECASE
        )
    return highlighted

@st.dialog("📝 Instructions", width="medium", dismissible=False)
def static_instructions(prolific_id, batch_id):
    st.title(f"Welcome to Batch #{batch_id}")
    st.markdown("""
    ### Before you begin, please read these instructions carefully.

    For this batch, you will complete **4 abstracts**. For each abstract, you will:
    1. **Term Familiarity:** For each term in the ABSTRACT, indicate whether you are familiar with it.  
    Then, specify what additional information (if any) would help you better understand the term.
    2. **Short Answer Questions:** Answer four questions using the **SUMMARY**, which is another version of the ABSTRACT. **Do NOT copy and paste from the SUMMARY** — doing so may risk not being compensated.  
    3. **Comparison Task:** Compare the SUMMARY to the original ABSTRACT by answering the comparison questions.
    ---
   **Additional Notes:**
    - Refer to the instructions at the top of each page for detailed guidance.  
    - You may open the sidebar at any time to log out.  
    - You can use the **Back** button to revisit earlier steps *within the same abstract*.  
    - Once you proceed to the next abstract, you will **not** be able to return to previous abstracts.

    Once you finish this batch, we will contact you with further instructions.
    """)
    if st.button("Start"):
        st.session_state.seen_static_instructions = True
        users_collection.update_one(
            {"prolific_id": prolific_id},
            {"$set": {f"phases.static.batches.{batch_id}.seen_instructions": True}},
            upsert=True
        )
        st.rerun()

def get_user_static_abstracts(prolific_id, batch_id):
    user = load_user(
        prolific_id,
        {f"phases.static.batches.{batch_id}.abstracts": 1, "_id": 0}
    )
    if not user:
        return []

    abstracts_dict = (
        user["phases"]["static"]["batches"][batch_id]["abstracts"]
    )

    abstracts = []

    for abstract_id in sorted(abstracts_dict.keys(), key=lambda x: int(x)):
        data = abstracts_dict[abstract_id]
        if not data.get("completed", False):
            abstracts.append({
                "abstract_id": abstract_id,
                "abstract_title": data.get("abstract_title", ""),
                "abstract": data.get("abstract", ""),
                "human_written_pls": data.get("human_written_pls", ""),
                "terms": data.get("term_familarity", [])
            })

    return abstracts


@st.fragment
def extra_info_fragment(abs_item, abstract_id):
    terms = [t["term"] for t in abs_item["terms"]]

    # Initialize state on first load
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
                    <div style="width:16px;height:16px;background-color:{color};
                    border-radius:4px;margin-right:10px;border:1px solid #ccc;"></div>
                    <div style="font-size:1.1rem;font-weight:600;">{idx+1}. {term}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_opts:
            base_key = f"extra_{abstract_id}_{idx}"
            # Read widget states
            def_key = f"{base_key}_def"
            ex_key = f"{base_key}_ex"
            bg_key = f"{base_key}_bg"
            none_key = f"{base_key}_none"

            # Current selection array
            current = st.session_state.extra_info_state.get(term, [])
            none_selected = ("None" in current)

            # Render checkboxes
            c1, c2, c3, c4 = st.columns([1, 1, 1, 1])

            with c1:
                def_val = st.checkbox(
                    "Definition",
                    key=def_key,
                    disabled=none_selected
                )
            with c2:
                ex_val = st.checkbox(
                    "Example",
                    key=ex_key,
                    disabled=none_selected
                )
            with c3:
                bg_val = st.checkbox(
                    "Background",
                    key=bg_key,
                    disabled=none_selected
                )
            with c4:
                none_val = st.checkbox(
                    "None",
                    key=none_key
                )

            # Build updated list
            if none_val:
                new_list = ["None"]
            else:
                new_list = []
                if def_val:
                    new_list.append("Definition")
                if ex_val:
                    new_list.append("Example")
                if bg_val:
                    new_list.append("Background")

            # Save back
            st.session_state.extra_info_state[term] = new_list

            cleaned_extra.append({
                "term": term,
                "extra_information": new_list
            })

    # Validate if all filled
    all_filled = all(len(row["extra_information"]) > 0 for row in cleaned_extra)

    # Navigation buttons
    col_back, _, _, _, _, col_next = st.columns(6)
    with col_back:
        back_clicked = st.button("⬅️ Back", key=f"back_extra_{abstract_id}")

    with col_next:
        next_clicked = st.button("Next ➡️", key=f"next_extra_{abstract_id}", disabled=not all_filled)

    return cleaned_extra, all_filled, back_clicked, next_clicked

def run_terms(prolific_id, batch_id, full_type):
    if st.session_state.get("current_batch_id") != batch_id:
        st.session_state.pop("seen_static_instructions", None)
        st.session_state.pop("next_static_abstract", None)
        st.session_state.current_batch_id = batch_id
    with st.sidebar:
        st.write(f"**MTurk ID:** `{prolific_id}`")
        if st.button("Logout"):
            st.session_state.show_logout_dialog = True
        if st.session_state.get("show_logout_dialog", False):
            logout_confirm_dialog(prolific_id)
            st.stop()
            
    if "fam_start_time" not in st.session_state:
        st.session_state.fam_start_time = None
    if "extra_start_time" not in st.session_state:
        st.session_state.extra_start_time = None
    if "time_familiarity" not in st.session_state:
        st.session_state.time_familiarity = 0
    if "time_extra_info" not in st.session_state:
        st.session_state.time_extra_info = 0
    # ------------------------------------------------ #

    # Instruction check
    user = load_user_info(prolific_id)
    db_seen = (
        user.get("phases", {})
            .get("static", {})
            .get("batches", {})
            .get(batch_id, {})
            .get("seen_instructions", False)
    )

    if "seen_static_instructions" not in st.session_state:
        st.session_state.seen_static_instructions = db_seen

    # If not seen → show instructions dialog
    if not st.session_state.seen_static_instructions:
        static_instructions(prolific_id, batch_id)
        return

    if "abstract_font_size" not in st.session_state:
        st.session_state.abstract_font_size = 16
    if "stage_static" not in st.session_state:
        st.session_state.stage_static = "familiarity"

    st.title("Term Familiarity")
    abs_item = None    
    abstracts = None     

    if "next_static_abstract" in st.session_state:
        n = st.session_state.next_static_abstract
        abs_item = {
            "abstract_id": n["abstract_id"],
            "abstract_title": n["abstract_title"],
            "abstract": n["abstract"],
            "human_written_pls": n.get("human_written_pls", ""),
            "terms": []
        }
        user = load_user(
            prolific_id,
            {f"phases.static.batches.{batch_id}.abstracts.{n['abstract_id']}": 1}
        )
        db_abs = user["phases"]["static"]["batches"][batch_id]["abstracts"][n["abstract_id"]]
        abs_item["terms"] = db_abs.get("term_familarity", [])
        abs_item["human_written_pls"] = db_abs.get("human_written_pls", "")
    else:
        abstracts = get_user_static_abstracts(prolific_id, batch_id)
        if not abstracts:
            st.success("🎉 All abstracts completed for this batch!")
            st.stop()

        abs_item = abstracts[0]

    abstract_id = abs_item["abstract_id"]
    current_abs_id = abs_item["abstract_id"]
    if st.session_state.get("current_term_abs_id") != current_abs_id:
        for key in [
            "updated_terms_tmp",
            "extra_info_state",
            "fam_start_time",
            "extra_start_time",
            "time_familiarity",
            "time_extra_info",
            "stage_static",
        ]:
            st.session_state.pop(key, None)
        st.session_state.stage_static = "familiarity"
        st.session_state.current_term_abs_id = current_abs_id

    completed, total = get_static_progress(prolific_id, batch_id)
    current_index = completed + 1
    st.progress(current_index / total)
    st.markdown(f"**Progress:** {current_index} / {total} abstracts")
    with st.expander("📝 Instructions", expanded=True):
        st.markdown("""
        1. Read the ABSTRACT — the 10 terms you will evaluate are **highlighted**.  
        2. Use the slider to rate how familiar you are with each term *in the context of the ABSTRACT*.  
        3. Click **Next** when you have finished rating all terms.  
        4. On the following page, select the additional information you would need for each term:  
        - You may select **all options that apply**.  
        - If **no additional information** is needed, choose **None** (do **not** select both None and other options).  

        **Note:** If you need to correct anything, please use the **Back** button to return to the previous page.
        """)
    st.markdown("### ABSTRACT")
    btn_col1, _, btn_col3 = st.columns([0.25, 0.65, 0.10])
    with btn_col1:
        if st.button("Decrease text size"):
            st.session_state.abstract_font_size = max(12, st.session_state.abstract_font_size - 2)
            st.rerun()
    with btn_col3:
        if st.button("Increase text size"):
            st.session_state.abstract_font_size = min(30, st.session_state.abstract_font_size + 2)
            st.rerun()

    abs_item["highlighted_html"] = cached_highlight(abs_item["abstract"], abs_item["terms"])
    abstract_fragment(abs_item, st.session_state.abstract_font_size)

    if st.session_state.stage_static == "familiarity":
        if st.session_state.get("fam_start_time") is None:
            st.session_state.fam_start_time = datetime.datetime.utcnow()

        updated_terms, next_clicked, all_fam_filled = familiarity_page(abs_item, abstract_id)
        if next_clicked:
            if st.session_state.fam_start_time:
                elapsed = (datetime.datetime.utcnow() - st.session_state.fam_start_time).total_seconds()
                st.session_state.time_familiarity += elapsed
                st.session_state.fam_start_time = None

            st.session_state.stage_static = "extra_info"
            st.session_state.updated_terms_tmp = updated_terms
            st.rerun()

        if not all_fam_filled:
            st.warning("⚠️ Please answer all familiarity questions before continuing.")
        return

    if st.session_state.stage_static == "extra_info":

       if st.session_state.get("extra_start_time") is None:
        st.session_state.extra_start_time = datetime.datetime.utcnow()

    cleaned_extra, all_filled, back_clicked, next_clicked = extra_info_fragment(abs_item, abstract_id)

    # Back
    if back_clicked:
        st.session_state.stage_static = "familiarity"
        st.rerun()

    # Next
    if next_clicked:
        if st.session_state.extra_start_time:
            elapsed = (datetime.datetime.utcnow() - st.session_state.extra_start_time).total_seconds()
            st.session_state.time_extra_info += elapsed
            st.session_state.extra_start_time = None

        final_terms = st.session_state.updated_terms_tmp
        for i, row in enumerate(cleaned_extra):
            final_terms[i]["extra_information"] = row["extra_information"]

        users_collection.update_one(
            {"prolific_id": prolific_id},
            {"$set": {
                f"phases.static.batches.{batch_id}.abstracts.{abstract_id}.term_familarity": final_terms,
                f"phases.static.batches.{batch_id}.abstracts.{abstract_id}.time_familiarity": st.session_state.time_familiarity,
                f"phases.static.batches.{batch_id}.abstracts.{abstract_id}.time_extra_info": st.session_state.time_extra_info
            }}
        )

        st.session_state.stage_static = "familiarity"
        st.switch_page("pages/static_short_answer.py")

    return

if "prolific_id" in st.session_state:
    run_terms(
        prolific_id=st.session_state.prolific_id,
        batch_id=st.session_state.batch_id,
        full_type=st.session_state.full_type
    )
else:
    print(">>>> ERROR: prolific_id missing when trying to run_chatbot", file=sys.stderr)

print(">>>> BOTTOM OF FILE REACHED", file=sys.stderr)
