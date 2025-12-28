from dotenv import load_dotenv
load_dotenv()
import db_utils
from datetime import datetime
import app_ui
import streamlit as st
from google.genai import types
from google import genai
from google.genai import types
import os

@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

client = get_gemini_client()


# first im checking the db cooncetion 
#db_conncection = db_utils.get_db_connection()

# print(db_conncection)

# session_id = 2
# timestamp = datetime.now()
# has_attachment = False
# insert_try= db_utils.try_message_insert(session_id, timestamp, "user", "Hello, how are you?", has_attachment)
# insert_try= db_utils.try_message_insert(session_id, timestamp, "assistant", "Hello,im good, what about you?", has_attachment)



# getting_history = db_utils.load_history(session_id)
# print(getting_history)


# def generate_response(user_message):
#     response = f"[System: {st.session_state['system_prompt'][:30]}...]"
    
#     if st.session_state["file_context"]:
#         response += f"\n\nFile context received ({len(st.session_state['file_context'])} chars)"
    
#     if st.session_state["image_data"]:
#         response += f"\n\nImage received: {st.session_state['image_data'].size}"
    
#     response += f"\n\nEcho: {user_message}"
    
#     return response
def generate_response(user_message):
    chat = get_or_create_chat_session(
        st.session_state["session_id"],
        st.session_state["system_prompt"]
    )

    message_parts = [user_message]

    if st.session_state["file_context"]:
        message_parts.append(st.session_state["file_context"])

    if st.session_state["image_data"]:
        message_parts.append(st.session_state["image_data"])

    response = chat.send_message(message_parts)

    return response.text


def get_or_create_chat_session(session_id, system_prompt):
    if "gemini_chat" in st.session_state:
        return st.session_state["gemini_chat"]

    history = db_utils.load_history(session_id)

    chat = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt
        )
    )

    if history:
        history = history[:-1]  

    for row in history:
        session_id_db, timestamp, role, content_text, has_attachment = row
        if role == "user":
            chat.send_message(content_text)

    st.session_state["gemini_chat"] = chat

    return chat


app_ui.initialize_session()
app_ui.display_sidebar()
st.title("💬 Gemini + DuckDB Local Chat")
app_ui.display_chat_history()

app_ui.display_file_uploader()

if prompt := st.chat_input("Type your message here..."):
    app_ui.handle_user_input(prompt, generate_response)



