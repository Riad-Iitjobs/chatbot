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
import os



def convert_csv_to_json(csv_file, max_rows=100):
    """Convert CSV to JSON with row limit to prevent large file issues"""
    data = {}

    text_file = io.StringIO(csv_file.getvalue().decode('utf-8'))

    csv_reader = csv.DictReader(text_file)
    row_count = 0

    for i, row in enumerate(csv_reader):
        if i >= max_rows:
            data["warning"] = f"CSV truncated: only first {max_rows} rows processed"
            break
        data[i] = row
        row_count += 1

    with open('output.json', 'w') as json_file:
        json.dump(data, json_file, indent=4)

    return json.dumps(data, indent=2)




def save_csv_to_disk(uploaded_file, session_id):
    """Save CSV file to disk and return path"""
    # Create uploads directory for this session
    upload_dir = f"uploads/{session_id}"
    os.makedirs(upload_dir, exist_ok=True)

    # Save file
    csv_path = os.path.join(upload_dir, uploaded_file.name)
    with open(csv_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return csv_path


def process_file(uploaded_file, session_id):
    """Process uploaded files and return context"""
    file_text_context = ""
    image_data = None
    csv_info = None

    file_type = uploaded_file.type

    if file_type == "application/pdf":
        pdf_reader = pypdf.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            extracted_text = page.extract_text()
            # Handle None or empty text safely
            if extracted_text:
                file_text_context += extracted_text

        # If no text was extracted from PDF
        if not file_text_context.strip():
            file_text_context = "[PDF uploaded but no text could be extracted]"

    elif file_type == "text/csv":
        # Save CSV to disk
        csv_path = save_csv_to_disk(uploaded_file, session_id)

        # Get schema from DuckDB
        schema_result = db_utils.get_csv_schema(csv_path)

        if schema_result["success"]:
            csv_info = {
                "path": csv_path,
                "filename": uploaded_file.name,
                "schema": schema_result["schema"]
            }
            file_text_context = f"[CSV uploaded: {uploaded_file.name}]"
        else:
            st.error(f"Failed to read CSV: {schema_result['error']}")
            file_text_context = "[CSV upload failed]"

    elif file_type in ["image/png", "image/jpeg", "image/jpg"]:
        image_data = Image.open(uploaded_file)
        file_text_context = f"[Image: {uploaded_file.name}]"

    return file_text_context, image_data, csv_info


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

    if "csv_info" not in st.session_state:
        st.session_state["csv_info"] = None

    if "stt_service" not in st.session_state:
        st.session_state["stt_service"] = None

    if "show_audio_recorder" not in st.session_state:
        st.session_state["show_audio_recorder"] = False

    if "transcribed_text" not in st.session_state:
        st.session_state["transcribed_text"] = ""


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
        file_context, image_data, csv_info = process_file(
            uploaded_file,
            st.session_state["session_id"]
        )
        st.session_state["file_context"] = file_context
        st.session_state["image_data"] = image_data
        st.session_state["csv_info"] = csv_info

        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f"✓ Attached: **{uploaded_file.name}**")
        with col2:
            if st.button("Remove", key="remove_file"):
                st.session_state["uploaded_file"] = None
                st.session_state["file_context"] = ""
                st.session_state["image_data"] = None
                st.session_state["csv_info"] = None
                st.rerun()

        # Display image preview
        if image_data:
            st.image(image_data, caption=uploaded_file.name, width=300)

        # Display CSV schema preview
        if csv_info:
            st.info("📊 **CSV Schema Detected:**")
            schema_text = ""
            for col in csv_info["schema"]:
                schema_text += f"• **{col['name']}** ({col['type']})\n"
            st.markdown(schema_text)
            st.caption("💡 You can now ask questions about this data!")


def display_voice_input():
    """Display microphone button and voice input interface"""
    st.markdown("---")

    col1, col2 = st.columns([1, 5])

    with col1:
        if st.button("🎤 Voice", help="Click to record voice input", use_container_width=True):
            st.session_state["show_audio_recorder"] = True
            st.rerun()

    with col2:
        if st.session_state.get("transcribed_text"):
            st.info(f"📝 Transcribed: {st.session_state['transcribed_text']}")

    # Show STT selector modal if microphone clicked
    if st.session_state.get("show_audio_recorder"):
        st.markdown("### 🎙️ Select Speech-to-Text Service")

        # STT service selection
        stt_option = st.radio(
            "Choose transcription method:",
            options=["whisper", "vosk"],
            format_func=lambda x: {
                "whisper": "🔷 Whisper (Higher accuracy, cloud-based)",
                "vosk": "⚡ Vosk (Faster, offline)"
            }[x],
            key="stt_selector"
        )

        st.session_state["stt_service"] = stt_option

        st.markdown("---")

        # Audio recorder
        st.markdown(f"**Recording with {stt_option.upper()}**")
        audio_value = st.audio_input("Click to record")

        if audio_value:
            with st.spinner(f"Transcribing with {stt_option.upper()}..."):
                try:
                    # Save audio temporarily
                    temp_audio_path = f"temp_audio_{st.session_state['session_id']}.wav"
                    with open(temp_audio_path, "wb") as f:
                        f.write(audio_value.getbuffer())

                    # Transcribe based on selected service
                    if stt_option == "whisper":
                        from stt_whisper_service import transcribe_audio_whisper
                        transcription = transcribe_audio_whisper(temp_audio_path)
                    else:  # vosk
                        from vosk_stt_service import transcribe_audio_vosk
                        transcription = transcribe_audio_vosk(temp_audio_path)

                    # Clean up temp file
                    if os.path.exists(temp_audio_path):
                        os.remove(temp_audio_path)

                    # Store transcription
                    st.session_state["transcribed_text"] = transcription
                    st.session_state["show_audio_recorder"] = False

                    st.success(f"✅ Transcribed: {transcription}")
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Transcription failed: {str(e)}")
                    # Clean up on error
                    if os.path.exists(temp_audio_path):
                        os.remove(temp_audio_path)

        # Cancel button
        if st.button("Cancel"):
            st.session_state["show_audio_recorder"] = False
            st.rerun()


def handle_user_input(prompt, generate_response_fn):
    has_attachment = st.session_state["uploaded_file"] is not None
    attachment_name = st.session_state["uploaded_file"].name if has_attachment else ""

    user_message = prompt
    if has_attachment:
        user_message = f"[Attached: {attachment_name}]\n{prompt}"

    try:
        # Generate assistant response FIRST (before saving anything)
        assistant_response = generate_response_fn(prompt)

        # Only save to database if response generation succeeded
        # Save user message to database
        db_utils.save_message(
            session_id=st.session_state["session_id"],
            timestamp=datetime.now(),
            role="user",
            content_text=user_message,
            has_attachment=has_attachment
        )

        # Save assistant message to database
        db_utils.save_message(
            session_id=st.session_state["session_id"],
            timestamp=datetime.now(),
            role="assistant",
            content_text=assistant_response,
            has_attachment=False
        )

        # Clear file attachments and messages to force reload from database
        st.session_state["uploaded_file"] = None
        st.session_state["file_context"] = ""
        st.session_state["image_data"] = None
        st.session_state["csv_info"] = None

        # Clear messages so they get reloaded from DuckDB on rerun
        if "messages" in st.session_state:
            del st.session_state["messages"]

        # Rerun to refresh UI and display clean history from DuckDB
        st.rerun()

    except Exception as e:
        # If API call failed, don't save anything to database
        st.error(f"Failed to generate response. Nothing was saved to database.")
        # Clear file attachments on error
        st.session_state["uploaded_file"] = None
        st.session_state["file_context"] = ""
        st.session_state["image_data"] = None
        st.session_state["csv_info"] = None
        st.stop()