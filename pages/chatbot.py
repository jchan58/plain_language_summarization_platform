import streamlit as st
from pymongo import MongoClient
from datetime import datetime
import pandas as pd
from openai import OpenAI
import streamlit.components.v1 as components
import markdown
import html

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


def render_message(content, role):
    formatted = markdown.markdown(content, extensions=["fenced_code", "tables"])
    safe_html = html.escape(formatted)
    return safe_html

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

def run_chatbot(prolific_id: str):
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

    abstracts = get_user_interactive_abstracts(prolific_id)
    if not abstracts:
        st.error("No interactive abstracts found for this user.")
        return

    for key, default in {
        "abstract_index": 0,
        "messages": [],
        "question_count": 0,
        "show_summary": False,
        "generated_summary": "",
    }.items():
        if key not in st.session_state:
            st.session_state[key] = default

    total = len(abstracts)
    idx = st.session_state.abstract_index
    if idx >= total:
        st.success("🎉 You've completed all interactive abstracts!")
        return

    abstract = abstracts[idx]
    abstract_id = abstract["abstract_id"]

    st.progress((idx + 1) / total)
    st.caption(f"Progress: {idx + 1} of {total} abstracts completed")
    st.markdown(
        """
        ### 📝 Instructions
        1. Read the scientific abstract on the **left side**.  
        2. Use the **question box** on the right to ask questions.  
        3. You must ask at least 3 questions.  
        4. When finished, click **“I'm done asking questions.”**  
        5. A plain-language summary will appear on the left. Please read this summary carefully. You’ll answer questions about it on the next page.
        6. Click **Next** to move to the next page after you feel that you are ready.  
        """
    )

    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.markdown(f"### 📘 {abstract['abstract_title']}")
        st.markdown(
            f"""
            <div style='background-color:#f2f3f5;
                        padding:1rem;
                        border-radius:0.5rem;
                        line-height:1.6;
                        border:1px solid #dcdcdc;'>
                {abstract['abstract']}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        if not st.session_state.show_summary and not st.session_state.get("generating_summary", False):
            st.markdown("### 💬 Chat with the Chatbot")
            messages = st.container(height=550, border=True)
            for msg in st.session_state.messages:
                messages.chat_message(msg["role"]).write(msg["content"])

            if not st.session_state.show_summary and not st.session_state.get("generating_summary", False):
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
                                {"role": "system", "content": f"Abstract:\n{abstract['abstract']}"},
                            ] + st.session_state.messages

                            response = client_openai.chat.completions.create(
                                model="gpt-4o",
                                messages=conversation_context,
                            )
                            full_response = response.choices[0].message.content.strip()

                            st.session_state.messages.append({"role": "assistant", "content": full_response})
                            st.markdown(full_response)

            # "I'm done asking" button
            if st.session_state.question_count >= 3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("✅ I'm done asking questions"):
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
                    st.session_state.generating_summary = True
                    st.rerun()

        elif st.session_state.get("generating_summary", False):
            with st.spinner("✨ Generating the summary, please wait..."):
                conversation_text = get_conversation()
                system_prompt = (
                    "You are an expert science communicator working with a reader who asked questions about a scientific abstract.\n\n"
                    f"Here is the conversation between the reader and an AI assistant:\n{conversation_text}\n\n"
                    "Use this conversation to identify what concepts, terms, or results the reader found confusing, interesting, or important. "
                    "Then rewrite the original abstract into a clear, accurate, plain-language summary."
                )

                response = client_openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Rewrite this abstract:\n\n{abstract['abstract']}"},
                    ],
                )
                summary = response.choices[0].message.content.strip()

                st.session_state.generated_summary = summary
                st.session_state.show_summary = True
                st.session_state.generating_summary = False
                st.rerun()

        if st.session_state.show_summary and not st.session_state.get("generating_summary", False):
            st.markdown("### 🧾 Summary of Scientific Abstract")
            st.markdown(
                f"<div style='background-color:#f5f7fa;padding:1rem;border-radius:0.5rem;'>"
                f"{st.session_state.generated_summary}</div>",
                unsafe_allow_html=True,
            )

            # CSS for true bottom-right fixed button across full width layout
            st.markdown(
                """
                <style>
                .next-btn-container {
                    position: fixed;
                    bottom: 40px;
                    right: 60px;
                    z-index: 9999;
                    pointer-events: none;  /* prevents layout issues */
                }
                .next-btn-container button {
                    pointer-events: auto;  /* re-enable interaction for the button itself */
                    background-color: #0066cc;
                    color: white;
                    border: none;
                    padding: 0.7rem 1.4rem;
                    border-radius: 6px;
                    font-size: 16px;
                    cursor: pointer;
                    box-shadow: 0 3px 6px rgba(0,0,0,0.15);
                }
                .next-btn-container button:hover {
                    background-color: #0052a3;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            # HTML wrapper for fixed positioning
            st.markdown('<div class="next-btn-container">', unsafe_allow_html=True)
            next_clicked = st.button("Next ➡️", key="next_button", help="Go to the next page")
            st.markdown('</div>', unsafe_allow_html=True)

            if next_clicked:
                st.session_state.last_completed_abstract = {
                    "prolific_id": prolific_id,
                    "abstract_id": abstract_id,
                    "title": abstract["abstract_title"],
                    "abstract": abstract["abstract"],
                    "pls": st.session_state.generated_summary 
                }

                st.session_state.show_summary = False
                st.session_state.generated_summary = ""
                st.session_state.messages = []
                st.session_state.question_count = 0
                st.session_state.abstract_index += 1
                st.switch_page("pages/short_answers.py")
