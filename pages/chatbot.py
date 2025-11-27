import streamlit as st
from pymongo import MongoClient
from datetime import datetime
import pandas as pd
from openai import OpenAI
import streamlit.components.v1 as components
import sys
print(">>>> ENTERED CHATBOT PAGE <<<<", file=sys.stderr)
print(">>>> chatbot.py LOADED", file=sys.stderr)
print("prolific_id IN SESSION? ", "prolific_id" in st.session_state, file=sys.stderr)
if "prolific_id" in st.session_state:
    print("VALUE = ", st.session_state.prolific_id, file=sys.stderr)
else:
    print("VALUE = MISSING", file=sys.stderr)
if "next_interactive_abstract" in st.session_state:
    print(">>>> next_interactive_abstract EXISTS:", 
          st.session_state["next_interactive_abstract"],
          type(st.session_state["next_interactive_abstract"]),
          file=sys.stderr)
else:
    print(">>>> next_interactive_abstract DOES NOT EXIST", file=sys.stderr)
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

@st.cache_resource
def get_openai_client():
    return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

db = get_mongo_client()["pls"]
users_collection = db["users"]
abstracts_collection = db["abstracts"]
client_openai = get_openai_client()

@st.cache_data
def load_example_users():
    return pd.read_csv("example_user.csv")

example_user_df = load_example_users()

st.markdown("""
    <style>
        /* Center the dialog title text */
        .stDialog > div > div > div:nth-child(1) {
            text-align: center !important;
            width: 100%;
        }
    </style>
""", unsafe_allow_html=True)


# Center the dialog title using CSS
st.markdown("""
    <style>
        .stDialog > div > div > div:nth-child(1) {
            text-align: center !important;
            width: 100%;
        }
    </style>
""", unsafe_allow_html=True)

def get_next_incomplete_abstract(prolific_id: str):
    user = users_collection.find_one(
        {"prolific_id": prolific_id},
        {"phases.interactive.abstracts": 1, "_id": 0}
    )

    if not user:
        return None

    abstracts = user["phases"]["interactive"]["abstracts"]
    for abstract_id in sorted(abstracts.keys(), key=lambda x: int(x)):
        a = abstracts[abstract_id]
        if not a.get("completed", False):
            return {
                "abstract_id": abstract_id,
                "abstract": a.get("abstract", ""),
                "abstract_title": a.get("abstract_title", "")
            }

    return None

@st.dialog("Are you sure you are done asking questions?", dismissible=False)
def show_done_dialog():

    # If generating_summary was triggered
    if st.session_state.get("dialog_generating", False):
        st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
        st.markdown("### ✍️ Generating SUMMARY...")
        st.markdown("Please wait.")
        st.spinner("")

        st.markdown("</div>", unsafe_allow_html=True)
        return 
    st.markdown(
        """You will be answering questions about this abstract on the next page and will not be able to return to this page."""
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        no_clicked = st.button("⬅️ No")

    with col2:
        yes_clicked = st.button("Yes ➡️")

    if no_clicked:
        st.rerun()

    if yes_clicked:
        st.session_state.generating_summary = True
        st.session_state.dialog_generating = True
        st.rerun()

def get_user_interactive_abstracts(prolific_id: str):
    user = users_collection.find_one(
        {"prolific_id": prolific_id},
        {"_id": 0, "phases.interactive.abstracts": 1}
    )
    if not user:
        return []
    abstracts_dict = user.get("phases", {}).get("interactive", {}).get("abstracts", {})
    abstracts = []
    for abstract_id, data in abstracts_dict.items():
        abstracts.append({
            "abstract_id": abstract_id,
            "abstract_title": data.get("abstract_title", ""),
            "abstract": data.get("abstract", "")
        })
    return abstracts

def get_conversation():
    return "\n".join(
        [f"{msg['role'].capitalize()}: {msg['content']}" for msg in st.session_state.messages]
    )

@st.dialog("📝 Instructions", width="medium", dismissible=False)
def interactive_instructions(prolific_id):
    st.markdown("""
    ### Before you begin
    Please follow these steps:
    - Read the scientific abstract on the **left side of the screen**.
    - Use the **chatbot** on the right to ask questions.
    - You must ask **at least 3 questions** before continuing.
    - When you’re done, click **“I'm done asking questions.”**
    - A **summary** will appear where the chatbot was — read it carefully.
    - Click **Next** to move to the comprehension page.
    ---
    """)

    if st.button("Start"):
        st.session_state.seen_interactive_instructions = True
        users_collection.update_one(
            {"prolific_id": prolific_id},
            {"$set": {"phases.interactive.seen_instructions": True}},
            upsert=True
        )
        st.rerun()

def run_chatbot(prolific_id: str):
    if not st.session_state.get("generating_summary", False):
        st.session_state.dialog_generating = False
    # set all the variables
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "question_count" not in st.session_state:
        st.session_state.question_count = 0
    if "show_summary" not in st.session_state:
        st.session_state.show_summary = False
    st.session_state.setdefault("generating_summary", False)
    # set the font size 
    if "abstract_font_size" not in st.session_state:
        st.session_state.abstract_font_size = 18
    if "next_interactive_abstract" in st.session_state:
        abstract_dict = st.session_state.next_interactive_abstract
    else:
        abstract_dict = get_next_incomplete_abstract(prolific_id)

    print(">>>> final abstract_dict:", abstract_dict, file=sys.stderr)

    if not abstract_dict:
        st.warning("No abstract available.")
        return

    # Use dict for titles, ids, metadata
    abstract_id = abstract_dict["abstract_id"]
    abstract_title = abstract_dict["abstract_title"]
    abstract = abstract_dict["abstract"]

    user = users_collection.find_one({"prolific_id": prolific_id})
    db_seen = (
        user.get("phases", {})
            .get("interactive", {})
            .get("seen_instructions", False)
    )

    if "seen_interactive_instructions" not in st.session_state:
        st.session_state.seen_interactive_instructions = db_seen
    if not st.session_state.seen_interactive_instructions:
        interactive_instructions(prolific_id)
        return
    st.title("💬 Chat with a chatbot about the scientific abstract")
    with st.sidebar:
        st.write(f"**MTurk ID:** `{prolific_id}`")
        if st.button("Logout"):
            users_collection.update_one(
                {"prolific_id": prolific_id},
                {"$set": {
                    "phases.interactive.last_completed_index": st.session_state.get("abstract_index", 0)
                }},
                upsert=True
            )
            for key in ["messages", "question_count", "show_summary", "generated_summary", "generating_summary"]:
                st.session_state.pop(key, None)
            st.switch_page("app.py")

    user = users_collection.find_one(
    {"prolific_id": prolific_id},
    {"phases.interactive.abstracts": 1, "_id": 0}
    )

    abstracts_dict = user["phases"]["interactive"]["abstracts"]
    total = len(abstracts_dict)
    completed = sum(1 for a in abstracts_dict.values() if a.get("completed", False))
    progress_ratio = completed / total if total > 0 else 0

    st.progress(progress_ratio)
    st.caption(f"Completed {completed} of {total} abstracts")
    st.markdown("""
    ### 📝 Instructions
    1. Read the scientific abstract on the **left side of the screen**.  
    2. Use the **chatbot** on the right to ask questions.  
    3. You must ask at least 3 questions.  
    4. When finished asking questions, click **“I'm done asking questions.”**  
    5. A SUMMARY will appear where the chatbot was — read it carefully.  
    6. Click **Next** to move on.  
    """)

    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.markdown(f"### ABSTRACT")
        btn_col1, btn_col2, btn_col3 = st.columns([0.25, 0.55, 0.20])
        with btn_col1:
            if st.button("Decrease text size"):
                st.session_state.abstract_font_size = max(12, st.session_state.abstract_font_size - 2)
                st.rerun()

        with btn_col2:
            st.write("")  # 

        with btn_col3:
            if st.button("Increase text size"):
                st.session_state.abstract_font_size = min(30, st.session_state.abstract_font_size + 2)
                st.rerun()
        formatted_abstract = abstract.replace("\n", "  \n")
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
                <div style="font-size: {st.session_state.abstract_font_size + 4}px; 
                            font-weight: 600; 
                            margin-bottom: 0.6rem;">
                    {abstract_title}
                </div>
                <div>
                    {formatted_abstract}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        if not st.session_state.get("show_summary", False) and not st.session_state.get("generating_summary", False):
            st.markdown("### 💬 Chat with the Chatbot")
            messages = st.container(height=550, border=True)
            for msg in st.session_state.messages:
                messages.chat_message(msg["role"]).write(msg["content"])

            if not st.session_state.get("show_summary", False) and not st.session_state.get("generating_summary", False):
                if prompt := st.chat_input("Type your question here..."):
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    st.session_state.question_count += 1
                    messages.chat_message("user").write(prompt)

                    with messages.chat_message("assistant"):
                        with st.spinner("🤔 Thinking..."):
                            conversation_context = [
                                {"role": "system", "content": (
                                    "You are a helpful assistant explaining scientific abstracts clearly and accurately. "
                                    "Use the abstract below to provide detailed but easy-to-understand answers."
                                )},
                                {"role": "system", "content": f"Abstract:\n{abstract}"},
                            ] + st.session_state.messages

                            response = client_openai.chat.completions.create(
                                model="gpt-4o",
                                messages=conversation_context,
                            )
                            full_response = response.choices[0].message.content.strip()

                            st.session_state.messages.append({"role": "assistant", "content": full_response})
                            st.markdown(full_response)

            # "I'm done asking" button
            done_disabled = st.session_state.question_count < 3
            st.markdown("<br>", unsafe_allow_html=True)
            done_clicked = st.button(
                "✅ I'm done asking questions",
                disabled=done_disabled,
                help="You must ask at least 3 questions before continuing."
            )

            if done_clicked and not done_disabled:
                conversation_log = [
                    {"role": m["role"], "content": m["content"], "timestamp": datetime.utcnow()}
                    for m in st.session_state.messages
                ]
                users_collection.update_one(
                    {"prolific_id": prolific_id},
                    {"$set": {
                        f"phases.interactive.abstracts.{abstract_id}.conversation_log": conversation_log
                    }},
                )
                show_done_dialog()

        elif st.session_state.get("generating_summary", False):
            with st.spinner(""):
                doc = users_collection.find_one(
                    {"prolific_id": prolific_id},
                    {"phases.interactive.abstracts": 1}
                )

                abstract_key = str(abstract_id)
                conversation_log = (
                    doc["phases"]["interactive"]["abstracts"]
                    .get(abstract_key, {})
                    .get("conversation_log", [])
                )

                conversation_text = "\n".join(
                    f"{msg['role'].capitalize()}: {msg['content']}"
                    for msg in conversation_log
                )
                system_prompt = (
                    "You are an expert science communicator. Rewrite the abstract into a personalized plain-language "
                    "summary that MUST incorporate all answers to the reader’s questions using the conversation.\n\n"
                    f"Conversation:\n{conversation_text}\n\n"
                    "Before writing the summary, do the following steps internally:\n"
                    "1. Extract every question the reader asked in the conversation.\n" 
                    "2. For each question, produce a short note describing the answer found in the conversation.\n"
                    "3. Then rewrite the abstract into a personalized plain-language summary that integrates ALL of these answers while preserving the content of the orginal abstract with no extraneous information.\n"
                    "4. Absolutely NO question may be omitted.\n" 
               )
                response = client_openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Rewrite this abstract:\n\n{abstract}"},
                    ],
                )
                summary = response.choices[0].message.content.strip()
                st.session_state.generated_summary = summary
                st.session_state.generating_summary = False
                st.session_state.dialog_generating = False
                st.session_state.last_completed_abstract = {
                    "prolific_id": prolific_id,
                    "abstract_id": abstract_id,
                    "title": abstract_title,
                    "abstract": abstract,
                    "pls": summary
                }
                users_collection.update_one(
                    {"prolific_id": prolific_id},
                    {"$set": {
                        f"phases.interactive.abstracts.{abstract_id}.summary": summary,
                    }}
                )
                st.session_state.messages = []
                st.session_state.question_count = 0
                for key in [
                    "feedback",
                    "main_idea",
                    "method",
                    "result",
                    "main_idea_text",
                    "method_text",
                    "result_text",
                ]:
                st.session_state.pop(key, None)
                st.switch_page("pages/short_answers.py")
if "prolific_id" in st.session_state:
    run_chatbot(st.session_state.prolific_id)
else:
    st.error("No MTurk / Prolific ID found in session. Please log in again.")
    print(">>>> ERROR: prolific_id missing when trying to run_chatbot", file=sys.stderr)

print(">>>> BOTTOM OF FILE REACHED", file=sys.stderr)