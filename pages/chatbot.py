import streamlit as st
from pymongo import MongoClient
from datetime import datetime
import pandas as pd
from openai import OpenAI
import json


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

    abstracts_dict = (
        user.get("phases", {})
            .get("interactive", {})
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

def get_conversation():
    lines = []
    for msg in st.session_state.messages:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


def run_chatbot(prolific_id: str):
    st.title("💬 Chat with a chatbot about the scientific abstract")
    abstracts = get_user_interactive_abstracts(prolific_id)
    if not abstracts:
        st.error("No interactive abstracts found for this user.")
        return
    if "abstract_index" not in st.session_state:
        user = users_collection.find_one({"prolific_id": prolific_id})
        abstracts_dict = user.get("phases", {}).get("interactive", {}).get("abstracts", {})
        uncompleted_ids = [aid for aid, data in abstracts_dict.items() if not data.get("completed", False)]

        if uncompleted_ids:
            for i, abs_data in enumerate(abstracts):
                if abs_data["abstract_id"] in uncompleted_ids:
                    st.session_state.abstract_index = i
                    break
        else:
            st.session_state.abstract_index = len(abstracts)
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "question_count" not in st.session_state:
        st.session_state.question_count = 0
    if "show_summary" not in st.session_state:
        st.session_state.show_summary = False
    if "generated_summary" not in st.session_state:
        st.session_state.generated_summary = ""

    total = len(abstracts)
    idx = st.session_state.abstract_index

    if idx >= total:
        st.success("🎉 You've completed all interactive abstracts!")
        return

    abstract = abstracts[idx]
    abstract_id = abstract["abstract_id"]

    st.progress((idx + 1) / total)
    st.caption(f"Progress: {idx + 1} of {total} abstracts completed")

    # add in instructions at the top 
    st.markdown(
    """
    ### 📝 Instructions
    1. Read the scientific abstract shown on the **left side of the screen**.  
    2. Use the **question box** to ask any questions you have about the abstract.
    3. You will have to ask at least 3 questions about the abstract. 
    4. When you are finished asking all your questions, click the **“I'm done asking questions”** button.  
    5. The system will then provide a **summary** — a short, easier-to-understand version of the abstract.  
    6. Review this summary to make sure it is clear to you before clicking the **Next** button.  
    """,
    )
    
  # --- Two-column layout ---
    col1, col2 = st.columns([1.3, 1])  # wider left column

    # LEFT COLUMN → Abstract & Summary
    with col1:
        st.markdown(f"### {abstract['abstract_title']}")
        st.write(abstract["abstract"])

        # If summary already generated, display it below
        if st.session_state.show_summary:
            st.divider()
            st.markdown("### 🧾 Summary of Scientific Abstract")
            st.write(st.session_state.generated_summary)

    # RIGHT COLUMN → Chat / Q&A
    with col2:
        st.markdown("### 💬 Ask Questions About This Abstract")

        # Show chat history
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input field
        if not st.session_state.show_summary:
            if prompt := st.chat_input("Type your question here..."):
                # Save question to session + DB
                st.session_state.messages.append({"role": "user", "content": prompt})
                st.session_state.question_count += 1

                with st.chat_message("user"):
                    st.markdown(prompt)

                # Generate AI answer
                with st.chat_message("assistant"):
                    placeholder = st.empty()
                    with st.spinner("🤔 Thinking..."):
                        response = client_openai.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "system", "content": "You are a helpful assistant explaining scientific abstracts."},
                                *st.session_state.messages,
                            ],
                        )
                    answer = response.choices[0].message.content
                    placeholder.markdown(answer)

                # Store assistant response
                st.session_state.messages.append({"role": "assistant", "content": answer})
                users_collection.update_one(
                    {"prolific_id": prolific_id},
                    {"$push": {
                        f"phases.interactive.abstracts.{abstract_id}.conversation_log": {
                            "user": prompt,
                            "assistant": answer,
                            "timestamp": datetime.utcnow()
                        }
                    }}
                )

        # "I'm done asking questions" button after 3 questions
        if st.session_state.question_count >= 3 and not st.session_state.show_summary:
            if st.button("I'm done asking questions"):
                # build conversation text
                conversation_text = "\n".join(
                    [f"{msg['role'].capitalize()}: {msg['content']}" for msg in st.session_state.messages]
                )

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
                            {"role": "user", "content": f"Rewrite this abstract:\n\n{abstract['abstract']}"}
                        ],
                    )

                summary = response.choices[0].message.content

                # Save to DB and update session
                users_collection.update_one(
                    {"prolific_id": prolific_id},
                    {"$set": {
                        f"phases.interactive.abstracts.{abstract_id}.pls": summary,
                        f"phases.interactive.abstracts.{abstract_id}.completed": True
                    }}
                )

                st.session_state.generated_summary = summary
                st.session_state.show_summary = True

        if st.session_state.show_summary:
            if st.button("Next"):
                st.session_state.show_summary = False
                st.session_state.generated_summary = ""
                st.session_state.messages = []
                st.session_state.question_count = 0
                st.session_state.abstract_index += 1
                st.switch_page("pages/short_answers.py")
