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

    col1, col2 = st.columns([1.3, 1], gap="large")
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

    with col2:
        st.markdown("### 💬 Chat with the Chatbot")
        st.markdown("""
        <style>
        .chat-container {
            height: 600px;
            overflow-y: auto;
            padding: 10px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background-color: #fafafa;
            display: flex;
            flex-direction: column;
        }
        .bubble-wrapper {
            display: flex;
            margin-bottom: 8px;
            width: 100%;
        }
        .user-bubble {
            background-color: #DCF8C6;
            color: black;
            padding: 10px 14px;
            border-radius: 16px;
            max-width: 75%;
            align-self: flex-start;
            margin-right: auto;
        }
        .assistant-bubble {
            background-color: #E8E8E8;
            color: black;
            padding: 10px 14px;
            border-radius: 16px;
            max-width: 75%;
            align-self: flex-end;
            margin-left: auto;
        }
        </style>
        """, unsafe_allow_html=True)

        # --- Input logic first (invisible, runs before UI) ---
        send = False
        user_input = st.session_state.get("pending_input", "")

        if "trigger_send" in st.session_state and st.session_state.trigger_send:
            # Handle sending message
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state.question_count += 1

            # Call OpenAI API
            conversation_context = [
                {"role": "system", "content": "You are a helpful assistant explaining scientific abstracts. "
                                            "Use the abstract below to answer clearly and accurately."},
                {"role": "system", "content": f"Abstract:\n{abstract['abstract']}"}
            ] + st.session_state.messages

            response = client_openai.chat.completions.create(
                model="gpt-4o",
                messages=conversation_context,
            )

            answer = response.choices[0].message.content.strip()
            st.session_state.messages.append({"role": "assistant", "content": answer})

            # Save to Mongo
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

            # Reset state to prevent loop
            st.session_state.trigger_send = False
            st.session_state.pending_input = ""
            st.rerun()

        # --- Render chat messages ---
        chat_html = '<div class="chat-container">'
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                chat_html += f'<div class="bubble-wrapper"><div class="user-bubble">{msg["content"]}</div></div>'
            else:
                chat_html += f'<div class="bubble-wrapper"><div class="assistant-bubble">{msg["content"]}</div></div>'
        chat_html += "</div>"
        st.markdown(chat_html, unsafe_allow_html=True)

        # --- Auto-scroll ---
        st.markdown("""
        <script>
        const chatDiv = window.parent.document.querySelector('.chat-container');
        if (chatDiv) { chatDiv.scrollTop = chatDiv.scrollHeight; }
        </script>
        """, unsafe_allow_html=True)

        # --- Ask your question below ---
        st.markdown("**Ask your question:**")
        with st.form("chat_input_form", clear_on_submit=True):
            cols = st.columns([4, 1])
            with cols[0]:
                st.session_state.pending_input = st.text_input(
                    " ", placeholder="Type your question here...", label_visibility="collapsed"
                )
            with cols[1]:
                send = st.form_submit_button("Send")

        if send and st.session_state.pending_input.strip():
            st.session_state.trigger_send = True
            st.rerun()


        # --- Input box below ---

        # if the number of questions is greater than 3 then we are good to move on
        if st.session_state.question_count >= 3 and not st.session_state.show_summary:
            if st.button("✅ I'm done asking questions", key="done_button"):
                st.session_state.generate_summary = True

        # --- Generate summary after rerun ---
        if st.session_state.get("generate_summary", False):
            st.session_state.generate_summary = False
            conversation_text = get_conversation()
            system_prompt = (
                "You are an expert science communicator working with a reader who asked questions about a scientific abstract.\n\n"
                f"Here is the conversation between the reader and an AI assistant:\n{conversation_text}\n\n"
                "Use this conversation to identify what concepts, terms, or results the reader found confusing, interesting, or important. "
                "Then rewrite the original abstract into a clear, accurate, plain-language summary."
            )

            with st.spinner("✨ Generating the summary..."):
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
