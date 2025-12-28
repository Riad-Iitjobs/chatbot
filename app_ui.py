import streamlit as st
import uuid
from datetime import datetime
import db_utils
from PIL import Image
import pandas as pd
import pypdf

import csv
import json
import io



def convert_csv_to_json(csv_file):
    data = {}
    
    text_file = io.StringIO(csv_file.getvalue().decode('utf-8'))
    
    csv_reader = csv.DictReader(text_file)
    for i, row in enumerate(csv_reader):
        data[i] = row  

    with open('output.json', 'w') as json_file:
        json.dump(data, json_file, indent=4)

    return json.dumps(data, indent=2)




def process_file(uploaded_file):
    """Process uploaded files and return context"""
    file_text_context = ""
    image_data = None
    
    file_type = uploaded_file.type
    
    if file_type == "application/pdf":
        pdf_reader = pypdf.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            file_text_context += page.extract_text()
    
    elif file_type == "text/csv":
        df = convert_csv_to_json(uploaded_file)
        file_text_context = df
    
    elif file_type in ["image/png", "image/jpeg", "image/jpg"]:
        image_data = Image.open(uploaded_file)
        file_text_context = f"[Image: {uploaded_file.name}]"
    
    return file_text_context, image_data


def initialize_session():
    query_params = st.query_params

    if "session_id" not in st.session_state:
        if "session_id" in query_params:
            st.session_state["session_id"] = query_params["session_id"]
        else:
            new_session_id = str(uuid.uuid4())
            st.session_state["session_id"] = new_session_id
            st.query_params["session_id"] = new_session_id

    if "messages" not in st.session_state:
        st.session_state["messages"] = []
        history = db_utils.load_history(st.session_state["session_id"])
        for row in history:
            st.session_state["messages"].append({
                "role": row[2],
                "content": row[3],
                "has_attachment": row[4]
            })

    if "system_prompt" not in st.session_state:
        st.session_state["system_prompt"] = "You are a helpful AI assistant."

    if "uploaded_file" not in st.session_state:
        st.session_state["uploaded_file"] = None

    if "file_context" not in st.session_state:
        st.session_state["file_context"] = ""

    if "image_data" not in st.session_state:
        st.session_state["image_data"] = None


def display_sidebar():
    st.sidebar.title("Session Info")
    st.sidebar.write(f"**Session ID:** `{st.session_state['session_id']}`")
    st.sidebar.caption("Each tab has a unique session")
    
    st.sidebar.divider()
    
    st.session_state["system_prompt"] = st.sidebar.text_area(
        "System Prompt",
        value=st.session_state["system_prompt"],
        height=150,
        help="Define how the AI should behave"
    )
    
    if st.sidebar.checkbox("Show all sessions in DB"):
        all_sessions = db_utils.get_all_sessions()
        st.sidebar.write("**All Sessions:**")
        for session in all_sessions:
            st.sidebar.write(f"- {session}")


def display_chat_history():
    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            if message.get("has_attachment"):
                st.caption("📎 Message with attachment")
            st.write(message["content"])


def display_file_uploader():
    """Display file uploader in the main chat area"""
    uploaded_file = st.file_uploader(
        "📎 Attach a file (optional)",
        type=["pdf", "csv", "png", "jpg", "jpeg"],
        help="Upload PDF, CSV, or Image files",
        key="file_uploader"
    )
    
    if uploaded_file is not None:
        st.session_state["uploaded_file"] = uploaded_file
        file_context, image_data = process_file(uploaded_file)
        st.session_state["file_context"] = file_context
        st.session_state["image_data"] = image_data
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f"✓ Attached: **{uploaded_file.name}**")
        with col2:
            if st.button("Remove", key="remove_file"):
                st.session_state["uploaded_file"] = None
                st.session_state["file_context"] = ""
                st.session_state["image_data"] = None
                st.rerun()
        
        if image_data:
            st.image(image_data, caption=uploaded_file.name, width=300)


def handle_user_input(prompt, generate_response_fn):
    has_attachment = st.session_state["uploaded_file"] is not None
    attachment_name = st.session_state["uploaded_file"].name if has_attachment else ""
    
    user_message = prompt
    if has_attachment:
        user_message = f"[Attached: {attachment_name}]\n{prompt}"
    
    with st.chat_message("user"):
        if has_attachment:
            st.caption(f"📎 Attached: {attachment_name}")
        st.write(prompt)
    
    st.session_state["messages"].append({
        "role": "user",
        "content": user_message,
        "has_attachment": has_attachment
    })
    
    db_utils.save_message(
        session_id=st.session_state["session_id"],
        timestamp=datetime.now(),
        role="user",
        content_text=user_message,
        has_attachment=has_attachment
    )
    
    assistant_response = generate_response_fn(prompt)
    
    with st.chat_message("assistant"):
        st.write(assistant_response)
    
    st.session_state["messages"].append({
        "role": "assistant",
        "content": assistant_response,
        "has_attachment": False
    })
    
    db_utils.save_message(
        session_id=st.session_state["session_id"],
        timestamp=datetime.now(),
        role="assistant",
        content_text=assistant_response,
        has_attachment=False
    )
    
    st.session_state["uploaded_file"] = None
    st.session_state["file_context"] = ""
    st.session_state["image_data"] = None