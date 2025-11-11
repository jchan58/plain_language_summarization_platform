import streamlit as st
from pymongo import MongoClient
from datetime import datetime
import pandas as pd
from openai import OpenAI

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

    abstracts = get_user_interactive_abstracts(prolific_id)
    if not abstracts:
        st.error("No interactive abstracts found for this user.")
        return

    # Initialize session state
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

    # Instructions
    st.markdown(
        """
        ### 📝 Instructions
        1. Read the scientific abstract on the **left side**.  
        2. Use the **question box** on the right to ask questions.  
        3. You must ask at least 3 questions.  
        4. When finished, click **“I'm done asking questions.”**  
        5. A plain-language summary will appear on the left.  
        6. Click **Next** to move to the next page after reviewing.  
        """
    )

    col1, col2 = st.columns([1.3, 1], gap="large")

    # ---------------- LEFT COLUMN ----------------
    with col1:
        st.markdown(f"### {abstract['abstract_title']}")
        st.write(abstract["abstract"])
        if st.session_state.show_summary:
            st.divider()
            st.markdown("### 🧾 Summary of Scientific Abstract")
            st.markdown(
                f"<div style='background-color:#f5f7fa;padding:1rem;border-radius:0.5rem;'>"
                f"{st.session_state.generated_summary}</div>",
                unsafe_allow_html=True,
            )

    # ---------------- RIGHT COLUMN (Chatbot) ----------------
    with col2:
        st.markdown("### 💬 Chat with the Chatbot")

        # CSS for scrollable chat area
        st.markdown(
            """
            <style>
            .chat-box {
                max-height: 500px;
                overflow-y: auto;
                padding: 10px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #fafafa;
                margin-bottom: 10px;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # Scrollable container for chat
        chat_container = st.container()
        with chat_container:
            st.markdown('<div class="chat-box">', unsafe_allow_html=True)
            for msg in st.session_state.messages:
                role = "🧑You" if msg["role"] == "user" else "🤖 Assistant"
                st.markdown(f"**{role}:** {msg['content']}")
            st.markdown("</div>", unsafe_allow_html=True)

        # "I'm done" button ABOVE the input box
        if st.session_state.question_count >= 3 and not st.session_state.show_summary:
            st.divider()
            if st.button("✅ I'm done asking questions"):
                conversation_text = get_conversation()
                system_prompt = (
                    "You are an expert science communicator working with a reader who asked questions about a scientific abstract.\n\n"
                    f"Here is the conversation between the reader and an AI assistant:\n{conversation_text}\n\n"
                    "Use this conversation to identify what concepts, terms, or results the reader found confusing, interesting, or important. "
                    "Then rewrite the original abstract into a clear, accurate, plain-language summary that preserves all key scientific details "
                    "but provides additional explanation and context for the specific parts the reader asked about or struggled to understand. "
                    "The goal is to make the abstract easier to understand while staying true to the science."
                )
                with st.spinner("✨ Generating the summary of the scientific abstract..."):
                    response = client_openai.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Rewrite this abstract:\n\n{abstract['abstract']}"},
                        ],
                    )
                summary = response.choices[0].message.content
                users_collection.update_one(
                    {"prolific_id": prolific_id},
                    {"$set": {
                        f"phases.interactive.abstracts.{abstract_id}.pls": summary,
                        f"phases.interactive.abstracts.{abstract_id}.completed": True,
                    }},
                )
                st.session_state.generated_summary = summary
                st.session_state.show_summary = True

        # Chat input form
        st.divider()
        st.markdown("**Ask your question:**")
        with st.form("chat_input_form", clear_on_submit=True):
            cols = st.columns([4, 1])
            with cols[0]:
                user_input = st.text_input(" ", placeholder="Type your question here...", label_visibility="collapsed")
            with cols[1]:
                send = st.form_submit_button("Send")

        # Handle send
        if send and user_input.strip():
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state.question_count += 1

            with st.spinner("🤔 Thinking..."):
                response = client_openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant explaining scientific abstracts."},
                        *st.session_state.messages,
                    ],
                )
            answer = response.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": answer})

            # Save conversation
            users_collection.update_one(
                {"prolific_id": prolific_id},
                {"$push": {
                    f"phases.interactive.abstracts.{abstract_id}.conversation_log": {
                        "user": user_input,
                        "assistant": answer,
                        "timestamp": datetime.utcnow(),
                    }
                }},
            )

            # Auto-scroll to bottom
            st.markdown(
                "<script>var chatBox = window.parent.document.querySelector('.chat-box');"
                "if(chatBox){chatBox.scrollTop = chatBox.scrollHeight;}</script>",
                unsafe_allow_html=True,
            )

            # Re-render the full message list inside the chat container
            with chat_container:
                st.markdown('<div class="chat-box">', unsafe_allow_html=True)
                for msg in st.session_state.messages:
                    role = "🧑You" if msg["role"] == "user" else "🤖 Assistant"
                    st.markdown(f"**{role}:** {msg['content']}")
                st.markdown("</div>", unsafe_allow_html=True)

        # Next button
        if st.session_state.show_summary:
            st.divider()
            if st.button("Next ➡️"):
                st.session_state.show_summary = False
                st.session_state.generated_summary = ""
                st.session_state.messages = []
                st.session_state.question_count = 0
                st.session_state.abstract_index += 1
                st.switch_page("pages/short_answers.py")

    # Divider between left and right columns
    st.markdown(
        """
        <style>
        section[data-testid="stHorizontalBlock"] > div:first-child {
            border-right: 2px solid #e0e0e0;
            padding-right: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
