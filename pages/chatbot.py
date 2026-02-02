import streamlit as st
from pymongo import MongoClient
import time
from datetime import datetime
import pandas as pd
from openai import OpenAI
import streamlit.components.v1 as components
import sys
from navigation import render_nav

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

@st.dialog("Are you sure you are done asking questions?", dismissible=False)
def show_done_dialog():
    if st.session_state.get("dialog_generating", False):
        st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
        st.markdown("### ✍️ Generating SUMMARY...")
        st.markdown("Please wait.")
        st.spinner("")
        st.markdown("</div>", unsafe_allow_html=True)
        return 
    st.markdown(
        """You will be answering questions about the SUMMARY derived from the ABSTRACT on the next page and will not be able to return to this page."""
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
        st.session_state.chat_duration_seconds = (time.time() - st.session_state.chat_start_time)
        st.rerun()

@st.dialog("Are you sure you want to log out?", dismissible=False)
def logout_confirm_dialog(prolific_id):
    # st.markdown(
    #     "Your progress will not be saved until you finish this abstract, which happens after you complete the **Compare SUMMARY to ABSTRACT Questionnaire**, click the **Next Abstract button**, and **confirm** that you want to move on.\n\n"
    #     "If you log out before then, you will have to start this abstract over."
    # )
    st.markdown(
        "Your progress will not be saved until you finish this abstract, which happens after you complete the **Compare SUMMARY to ABSTRACT Questionnaire**, click the **Next Batch button**, and **confirm** that you want to move on.\n\n"
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

def get_conversation():
    return "\n".join(
        [f"{msg['role'].capitalize()}: {msg['content']}" for msg in st.session_state.messages]
    )

@st.dialog("📝 Instructions", width="medium", dismissible=False)
def interactive_instructions(prolific_id, batch_id):
    st.title(f"Welcome to Phase 2")
    # st.title(f"Welcome to Batch #{batch_id}")
    # st.markdown("""
    # ### Before you begin, please read these instructions carefully  
    # Please follow these steps:

    # For this batch, you will complete **3 abstracts**. For each abstract, you will:

    # 1. **Chat with the AI chatbot about the ABSTRACT:** After reading the ABSTRACT, ask the AI chatbot any questions you have to help you better understand it.
    # 2. **Select All That Apply (SATA) Questions:** Answer all five SATA questions using the **SUMMARY** derived from the ABSTRACT.  
    # 3. **Compare SUMMARY to ABSTRACT Questionnaire:** Answer the questions on the page to assess how the SUMMARY compares to the ABSTRACT in terms of clarity, organization, coverage of information, inclusion of background information, and trustworthiness, and complete a few questions about your AI chatbot experience in this study.
    # ---
    # **Additional Notes:**
    # - Refer to the instructions at the top of each page for detailed guidance.  
    # - Your progress is **not automatically saved** as you go. Your progress is only saved when you finish the current abstract by completing the **Compare SUMMARY to ABSTRACT Questionnaire** , clicking the **Next Abstract** button, and **confirming** that you want to move on to the next abstract.  
    # - You may open the sidebar at any time to log out. However, if you log out before finishing the abstract in progresss, Your progress for that abstract will not be saved, and you will have to recomplete that same abstract when you log back in.
    # - You may use the **Back** button to revisit earlier steps *within the same abstract*.  
    # - Once you move on to the next abstract, you will **not** be able to return to previous abstracts.
    # ---
    # Once you finish this batch, we will contact you with further instructions.       
    # """)
    st.markdown("""
    ### Before you begin, please read these instructions carefully  
    Please follow these steps:

     For this interactive phase, you will complete **1 abstract**. First, read the abstract. Then you will be asked to do the following.

    1. After reading the ABSTRACT, use the AI chatbot to ask any questions you have to help you better understand the content and any questions you may have:
       \n**For example:**\n
        “Is this medication FDA approved for me to take?”
    2. You will then be shown a SUMMARY derived from the ABSTRACT. Read the SUMMARY and answer all five Select-All-That-Apply (SATA) questions using the information provided in the SUMMARY.
    3. You will then be shown both the ABSTRACT and the SUMMARY and asked to complete the following:\n
        (a) Comparing the SUMMARY to the ABSTRACT:
                
        Answer questions that evaluate how the SUMMARY compares to the ABSTRACT in terms of clarity, organization, coverage of information, inclusion of background information, and trustworthiness.

        (b) Thinking only about the SUMMARY:
                
        Answer questions that assess the SUMMARY on its own, including whether it met your information needs.

        (c) Your experience using the AI chatbot:
                
        Answer a few questions about your experience using the AI chatbot in this study.
    ---
    **Additional Notes:**
    - Refer to the instructions at the top of each page for detailed guidance.  
    - Your progress is **not automatically saved** as you go. Your progress is only saved when you finish the current abstract by completing the **Compare SUMMARY to ABSTRACT Questionnaire** , clicking the **Next Abstract** button, and **confirming** that you want to move on to the next abstract.  
    - You may open the sidebar at any time to log out. However, if you log out before finishing the abstract in progresss, Your progress for that abstract will not be saved, and you will have to recomplete that same abstract when you log back in.
    - You may use the **Back** button to revisit earlier steps *within the same abstract*.  
    ---
    - Once you finish this batch, please record your time on how long it took you to complete this batch and the Select All That Apply (SATA) questions in seconds on the page after the **Compare SUMMARY to ABSTRACT Questionnaire.**  
    - You will also be able to leave any optional feedback about the task, instructions, or your experience.
    """)

    if st.button("Start"):
        st.session_state.seen_interactive_instructions = True
        users_collection.update_one(
            {"prolific_id": prolific_id},
            {"$set": {f"phases.interactive.batches.{batch_id}.seen_instructions": True}},
            upsert=True
        )
        st.rerun()

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

def get_next_incomplete_abstract(prolific_id: str, batch_id: str):
    user = users_collection.find_one(
        {"prolific_id": prolific_id},
        {f"phases.interactive.batches.{batch_id}.abstracts": 1, "_id": 0}
    )

    if not user:
        return None

    abstracts = (
        user.get("phases", {})
            .get("interactive", {})
            .get("batches", {})
            .get(batch_id, {})
            .get("abstracts", {})
    )

    print("DEBUG abstracts keys:", abstracts.keys())
    for abstract_id in sorted(abstracts.keys(), key=lambda x: int(x)):
        a = abstracts[abstract_id]
        if not a.get("completed", False):
            return {
                "abstract_id": abstract_id,
                "abstract": a.get("abstract", ""),
                "abstract_title": a.get("abstract_title", "")
            }
    return None

# get all the interactive abstracts in the batch
def get_user_interactive_abstracts(prolific_id: str, batch_id: str):
    user = users_collection.find_one(
        {"prolific_id": prolific_id},
        {f"phases.interactive.batches.{batch_id}.abstracts": 1, "_id": 0}
    )
    if not user:
        return []

    abstracts_dict = (
        user.get("phases", {})
            .get("interactive", {})
            .get("batches", {})
            .get(batch_id, {})
            .get("abstracts", {})
    )
    abstracts = []
    for abstract_id, data in abstracts_dict.items():
        abstracts.append({
            "abstract_id": abstract_id,
            "abstract_title": data.get("abstract_title", ""),
            "abstract": data.get("abstract", "")
        })
    return abstracts

def format_sata(sata_list):
    out = []
    for i, q in enumerate(sata_list, 1):
        out.append(f"SATA {i}: {q['question']}")
        for j, opt in enumerate(q["options"], 1):
            out.append(f"  {j}. {opt}")
        out.append(f"Correct answers: {', '.join(q['correct_answers'])}")
        out.append("")
    return "\n".join(out)

def build_conversation_text(conversation_log):
    user_messages = [
        msg["content"].strip()
        for msg in conversation_log
        if msg.get("role") == "user" and msg.get("content")
    ]

    if not user_messages:
        raise ValueError("No user questions found in conversation log")

    return "\n".join(f"User: {q}" for q in user_messages)

def parse_choices(s):
    if not s:
        return []
    return [x.strip() for x in str(s).split(";") if x.strip()]

def build_sata_questions(abstract_info):
    sata_questions = []
    allowed_questions = {1, 2, 3, 5}

    for i in allowed_questions:
        q_key = f"question_{i}"
        choices_key = f"question_{i}_answers_choices"
        correct_key = f"question_{i}_correct_answers"
        if q_key not in abstract_info:
            continue

        sata_questions.append({
            "question": abstract_info[q_key],
            "options": parse_choices(abstract_info.get(choices_key, "")),
            "correct_answers": parse_choices(abstract_info.get(correct_key, "")),
        })

    if not sata_questions:
        raise ValueError("No valid SATA questions found after filtering")

    return sata_questions

def run_chatbot(prolific_id, batch_id, full_type):
    # detect batch change 
    if st.session_state.get("current_batch_id") != batch_id:
        st.session_state.pop("seen_interactive_instructions", None)
        st.session_state.current_batch_id = batch_id
    # set the variables 
    if "chat_start_time" not in st.session_state:
        st.session_state.chat_start_time = time.time()
    if not st.session_state.get("generating_summary", False):
        st.session_state.dialog_generating = False
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


    # get the next abstract
    if "next_interactive_abstract" in st.session_state:
        abstract_dict = st.session_state.next_interactive_abstract
        batch_id = abstract_dict["batch_id"]
        full_type = abstract_dict["full_type"]
    else:
        abstract_dict = get_next_incomplete_abstract(prolific_id, batch_id)

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
            .get("batches", {})
            .get(batch_id, {})
            .get("seen_instructions", False)
    )
    if "seen_interactive_instructions" not in st.session_state:
        st.session_state.seen_interactive_instructions = db_seen
    if not st.session_state.seen_interactive_instructions:
        interactive_instructions(prolific_id, batch_id)
        return
    st.title("💬 Chat with a chatbot about the scientific abstract")
    with st.sidebar:
        st.write(f"**MTurk ID:** `{prolific_id}`")
        if st.button("Logout"):
            st.session_state.show_logout_dialog = True
        if st.session_state.get("show_logout_dialog", False):
            st.session_state.show_logout_dialog = False 
            logout_confirm_dialog(prolific_id)

    user = users_collection.find_one(
    {"prolific_id": prolific_id},
    {f"phases.interactive.batches.{batch_id}.abstracts": 1, "_id": 0}
    )

    abstracts_dict = (
        user.get("phases", {})
            .get("interactive", {})
            .get("batches", {})
            .get(batch_id, {})
            .get("abstracts", {})
    )
    total = len(abstracts_dict)
    completed = sum(1 for a in abstracts_dict.values() if a.get("completed", False))
    current = completed
    progress_ratio = current / total if total > 0 else 0
    st.progress(progress_ratio)
    st.caption(f"Completed {current} of {total} abstracts")
    with st.expander("📝 Instructions", expanded=True):
        st.markdown("""
        1. Read the ABSTRACT on the **left side of the screen**.  
        2. Use the **chatbot** on the right to ask questions about anything in the ABSTRACT you would like to understand better.  
        3. You must ask the chatbot **at least 3 questions** before moving on.  
        4. When you are finished asking questions, click **“I'm done asking questions.”**  
        5. A confirmation popup will appear — please confirm that you would like to move on to the next task.\n\n
        **Note:** Once you move on, you will **not** be able to return to this page.
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

            with st.expander("🧾 Conversation So Far"):
                for msg in st.session_state.messages:
                    st.markdown(f"**{msg['role'].capitalize()}:** {msg['content']}")

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
                        f"phases.interactive.batches.{batch_id}.abstracts.{abstract_id}.conversation_log": conversation_log
                    }},
                )
                show_done_dialog()

        elif st.session_state.get("generating_summary", False):
            with st.spinner(""):
                doc = users_collection.find_one(
                    {"prolific_id": prolific_id},
                    {f"phases.interactive.batches.{batch_id}.abstracts": 1, "_id": 0}
                )

                abstract_key = str(abstract_id)
                abstracts_dict = (
                    doc.get("phases", {})
                    .get("interactive", {})
                    .get("batches", {})
                    .get(batch_id, {})
                    .get("abstracts", {})
                )
                conversation_log = (
                    abstracts_dict
                        .get(abstract_key, {})
                        .get("conversation_log", [])
                )
                conversation_text = build_conversation_text(conversation_log)
                print(conversation_text)
                abstract_info = abstracts_dict.get(abstract_key, {})
                sata_list = build_sata_questions(abstract_info)
                sata_text = format_sata(sata_list)
                print(sata_text)
                system_prompt = (
                    "CRITICAL RULE:\n"
                    "If the user asks 'why' or 'how' and the abstract does not give a reason, you MUST include an explicit sentence saying the reason is unknown or not well understood.\n\n"

                    "You are an expert science communicator.\n\n"
                    "Your task is to rewrite the abstract into a personalized, plain-language summary for this specific reader.\n\n"
                    "You MUST use the questions the user is confused about below to understand what the user is confused about or curious about, "
                    "and make sure those topics are clearly explained in the rewritten abstract.\n\n"
                    f"Questions:\n{conversation_text}\n\n"
                    f"Select-All-That-Apply (SATA) Questions:\n{sata_text}\n\n"
                    "For each SATA item:\n"
                    "- The rewritten summary MUST contain information that allows a careful reader to logically deduce every correct answer.\n"
                    "- You must NOT explicitly list, label, or reference answer choices or say which options are correct inside the summary.\n"
                    "- The summary MUST avoid adding statements that would also justify incorrect options.\n"
                    "- Add background knowledge only if it is necessary to answer a user question or enable SATA deduction.\n"
                    "- The summary must remain natural narrative, not exam-style reasoning.\n\n"
                    "Follow these steps internally (do NOT show them in your final answer):\n"
                    "1. Identify every user question in the conversation text.\n"
                    "2. For each user question:\n"
                    "   - If the abstract contains the answer, explain it clearly using only abstract content.\n"
                    "   - If not, add only the minimal well-established background needed to answer it.\n"
                    "   - For any 'why' or 'how' question, include a causal explanation.\n"
                    "   - If a user asks 'why' or 'how' and the abstract does not provide a reason, you MUST include an explicit sentence stating that the reason is unknown or not well understood.\n"
                    "3. For each SATA question:\n"
                    "   - Identify what facts allow correct options to be inferred.\n"
                    "   - Embed those facts naturally in the summary.\n"
                    "   - Ensure no incorrect option is supported.\n"
                    "4. Final internal check:\n"
                    "   - Every user question is answered by at least one sentence.\n"
                    "   - No sentence exists that does not help answer a user question or support SATA deduction.\n"
                    "   - No incorrect SATA option is supported.\n"
                    "   - If any condition fails, rewrite until all pass.\n\n"
                    "Final output rules:\n"
                    "- Output only the final personalized plain-language summary.\n"
                    "- Do NOT show reasoning steps, checklists, or internal notes.\n"
                    "- If any user question is not clearly answered, the output is wrong.\n"
                    "- Do not add information that does not serve answering user questions or enabling SATA deduction."
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
                    "phase_type": "interactive",
                    "batch_id": batch_id,
                    "full_type": full_type,
                    "abstract_id": abstract_id,
                    "title": abstract_title,
                    "abstract": abstract,
                    "pls": summary,
                }
                st.session_state.progress_info = {
                    "current": current,
                    "total": total
                }
                users_collection.update_one(
                    {"prolific_id": prolific_id},
                    {"$set": {
                        f"phases.interactive.batches.{batch_id}.abstracts.{abstract_id}.summary": summary,
                        f"phases.interactive.batches.{batch_id}.abstracts.{abstract_id}.chat_duration_seconds": st.session_state.chat_duration_seconds
                    }}
                )
                if "chat_start_time" in st.session_state:
                    st.session_state.pop("chat_start_time")
                st.session_state.messages = []
                st.session_state.question_count = 0
                for key in [
                    "qa_index",
                    "feedback",
                    "main_idea_box",
                    "method_box",
                    "result_box",
                ]:
                    if key in st.session_state:
                        st.session_state.pop(key)
                users_collection.update_one(
                    {"prolific_id": prolific_id},
                    {"$set": {
                        "last_page": "chatbot",
                        "last_batch": batch_id,
                        "last_abs_id": abstract_id,
                        "last_full_type": full_type
                    }}
                )
                st.switch_page("pages/short_answers.py")


if "prolific_id" in st.session_state:
    run_chatbot(
        prolific_id=st.session_state.prolific_id,
        batch_id=st.session_state.batch_id,
        full_type=st.session_state.full_type
    )
else:
    print(">>>> ERROR: prolific_id missing when trying to run_chatbot", file=sys.stderr)

print(">>>> BOTTOM OF FILE REACHED", file=sys.stderr)
