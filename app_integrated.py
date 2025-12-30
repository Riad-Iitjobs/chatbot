from dotenv import load_dotenv
load_dotenv()

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
import requests
from google.genai import types
from google import genai

# ============================================================================
# CONFIGURATION
# ============================================================================

WHISPER_SERVER_URL = "http://localhost:8001"
OCR_SERVER_URL = "http://localhost:8002"

@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

client = get_gemini_client()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_server_health(server_url, server_name):
    """Check if a server is running"""
    try:
        response = requests.get(f"{server_url}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


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
    upload_dir = f"uploads/{session_id}"
    os.makedirs(upload_dir, exist_ok=True)
    csv_path = os.path.join(upload_dir, uploaded_file.name)
    with open(csv_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return csv_path


def transcribe_audio_via_server(audio_file):
    """Send audio to Whisper server for transcription"""
    try:
        # Save temp file
        temp_path = f"temp_audio_{st.session_state['session_id']}.wav"
        with open(temp_path, "wb") as f:
            f.write(audio_file.getbuffer())

        # Send to Whisper server
        with open(temp_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{WHISPER_SERVER_URL}/transcribe", files=files, timeout=60)

        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return result.get("transcription", "")
            else:
                raise Exception(result.get("error", "Unknown error"))
        else:
            raise Exception(f"Server returned {response.status_code}")

    except Exception as e:
        raise Exception(f"Whisper server error: {str(e)}")


def extract_text_via_ocr_server(image_file):
    """Send image to OCR server for text extraction"""
    try:
        # Save temp file
        file_ext = os.path.splitext(image_file.name)[1] or '.jpg'
        temp_path = f"temp_image_{st.session_state['session_id']}{file_ext}"
        with open(temp_path, "wb") as f:
            f.write(image_file.getbuffer())

        # Send to OCR server
        with open(temp_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{OCR_SERVER_URL}/ocr", files=files, timeout=60)

        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return {
                    "text": result.get("text", ""),
                    "lines": result.get("lines", []),
                    "confidence": sum([line["confidence"] for line in result.get("lines", [])]) / len(result.get("lines", [])) if result.get("lines") else 0
                }
            else:
                raise Exception(result.get("error", "Unknown error"))
        else:
            raise Exception(f"Server returned {response.status_code}")

    except Exception as e:
        raise Exception(f"OCR server error: {str(e)}")


def process_file(uploaded_file, session_id, ocr_mode="vision"):
    """Process uploaded files and return context"""
    file_text_context = ""
    image_data = None
    csv_info = None
    audio_transcription = None
    ocr_result = None

    file_type = uploaded_file.type

    # PDF processing
    if file_type == "application/pdf":
        pdf_reader = pypdf.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                file_text_context += extracted_text
        if not file_text_context.strip():
            file_text_context = "[PDF uploaded but no text could be extracted]"

    # CSV processing
    elif file_type == "text/csv":
        csv_path = save_csv_to_disk(uploaded_file, session_id)
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

    # Image processing
    elif file_type in ["image/png", "image/jpeg", "image/jpg", "image/webp"]:
        image_data = Image.open(uploaded_file)

        if ocr_mode == "ocr":
            # Send to OCR server
            uploaded_file.seek(0)  # Reset file pointer
            ocr_result = extract_text_via_ocr_server(uploaded_file)
            file_text_context = f"[OCR extracted from {uploaded_file.name}]:\n{ocr_result['text']}"
        else:
            # Use Gemini Vision
            file_text_context = f"[Image: {uploaded_file.name}]"

    # Audio processing (new!)
    elif file_type in ["audio/mpeg", "audio/wav", "audio/mp3", "audio/x-wav"]:
        uploaded_file.seek(0)
        audio_transcription = transcribe_audio_via_server(uploaded_file)
        file_text_context = f"[Audio transcription from {uploaded_file.name}]:\n{audio_transcription}"

    return file_text_context, image_data, csv_info, audio_transcription, ocr_result


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

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

    if "audio_transcription" not in st.session_state:
        st.session_state["audio_transcription"] = None

    if "ocr_result" not in st.session_state:
        st.session_state["ocr_result"] = None

    if "stt_service" not in st.session_state:
        st.session_state["stt_service"] = None

    if "show_audio_recorder" not in st.session_state:
        st.session_state["show_audio_recorder"] = False

    if "transcribed_text" not in st.session_state:
        st.session_state["transcribed_text"] = ""

    if "image_processing_mode" not in st.session_state:
        st.session_state["image_processing_mode"] = "vision"


# ============================================================================
# UI COMPONENTS
# ============================================================================

def display_sidebar():
    st.sidebar.title("🔧 Configuration")

    # Server status
    st.sidebar.subheader("Server Status")
    whisper_status = check_server_health(WHISPER_SERVER_URL, "Whisper")
    ocr_status = check_server_health(OCR_SERVER_URL, "OCR")

    st.sidebar.write(f"{'🟢' if whisper_status else '🔴'} Whisper (8001): {'Running' if whisper_status else 'Offline'}")
    st.sidebar.write(f"{'🟢' if ocr_status else '🔴'} OCR (8002): {'Running' if ocr_status else 'Offline'}")

    st.sidebar.divider()

    # Session info
    st.sidebar.subheader("Session Info")
    st.sidebar.write(f"**Session ID:** `{st.session_state['session_id'][:8]}...`")
    st.sidebar.caption("Each tab has a unique session")

    st.sidebar.divider()

    # System prompt
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
    """Display file uploader with OCR option for images"""
    uploaded_file = st.file_uploader(
        "📎 Attach a file (optional)",
        type=["pdf", "csv", "png", "jpg", "jpeg", "webp", "mp3", "wav"],
        help="Upload PDF, CSV, Image, or Audio files",
        key="file_uploader"
    )

    if uploaded_file is not None:
        file_type = uploaded_file.type

        # Show OCR option for images only
        if file_type in ["image/png", "image/jpeg", "image/jpg", "image/webp"]:
            ocr_available = check_server_health(OCR_SERVER_URL, "OCR")

            if ocr_available:
                st.session_state["image_processing_mode"] = st.radio(
                    "Image Processing Mode:",
                    options=["vision", "ocr"],
                    format_func=lambda x: {
                        "vision": "🔷 Gemini Vision (AI understands image)",
                        "ocr": "📄 OCR (Extract text only)"
                    }[x],
                    horizontal=True,
                    key="image_mode_selector"
                )
            else:
                st.warning("⚠️ OCR server offline. Using Gemini Vision.")
                st.session_state["image_processing_mode"] = "vision"

        # Process file
        st.session_state["uploaded_file"] = uploaded_file
        file_context, image_data, csv_info, audio_transcription, ocr_result = process_file(
            uploaded_file,
            st.session_state["session_id"],
            st.session_state.get("image_processing_mode", "vision")
        )
        st.session_state["file_context"] = file_context
        st.session_state["image_data"] = image_data
        st.session_state["csv_info"] = csv_info
        st.session_state["audio_transcription"] = audio_transcription
        st.session_state["ocr_result"] = ocr_result

        # Display file info
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f"✓ Attached: **{uploaded_file.name}**")
        with col2:
            if st.button("Remove", key="remove_file"):
                st.session_state["uploaded_file"] = None
                st.session_state["file_context"] = ""
                st.session_state["image_data"] = None
                st.session_state["csv_info"] = None
                st.session_state["audio_transcription"] = None
                st.session_state["ocr_result"] = None
                st.rerun()

        # Display previews
        if image_data:
            st.image(image_data, caption=uploaded_file.name, width=300)
            if ocr_result:
                st.info(f"📊 **OCR Confidence:** {ocr_result['confidence']:.1%}")
                with st.expander("View extracted text"):
                    st.text(ocr_result['text'])

        if csv_info:
            st.info("📊 **CSV Schema Detected:**")
            schema_text = ""
            for col in csv_info["schema"]:
                schema_text += f"• **{col['name']}** ({col['type']})\n"
            st.markdown(schema_text)
            st.caption("💡 You can now ask questions about this data!")

        if audio_transcription:
            st.info("🎵 **Audio Transcription:**")
            st.text(audio_transcription)


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
        st.markdown("### 🎙️ Record Voice Input")

        # Check Whisper server status
        whisper_available = check_server_health(WHISPER_SERVER_URL, "Whisper")

        if not whisper_available:
            st.error("⚠️ Whisper server is offline! Please start it: `python whisper_model/whisper_server.py`")
            if st.button("Cancel"):
                st.session_state["show_audio_recorder"] = False
                st.rerun()
            return

        st.markdown("**Recording with Whisper Server**")
        audio_value = st.audio_input("Click to record")

        if audio_value:
            with st.spinner("Transcribing with Whisper Server..."):
                try:
                    # Transcribe via Whisper server
                    transcription = transcribe_audio_via_server(audio_value)

                    # Store transcription
                    st.session_state["transcribed_text"] = transcription
                    st.session_state["show_audio_recorder"] = False

                    st.success(f"✅ Transcribed: {transcription}")
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Transcription failed: {str(e)}")

        # Cancel button
        if st.button("Cancel"):
            st.session_state["show_audio_recorder"] = False
            st.rerun()


# ============================================================================
# RESPONSE GENERATION
# ============================================================================

def generate_sql_query(user_question, csv_schema):
    """Generate SQL query using Gemini for CSV Q&A"""
    try:
        schema_text = ", ".join([f"{col['name']} ({col['type']})" for col in csv_schema])

        prompt = f"""You are a SQL expert for DuckDB.

The user has uploaded a CSV with these columns:
{schema_text}

User question: "{user_question}"

Write a DuckDB SQL query to answer this question. Use "csv_data" as the table name.
Return ONLY the SQL query, no explanation or markdown formatting."""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        sql_query = response.text.strip()
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

        return sql_query

    except Exception as e:
        raise Exception(f"Failed to generate SQL: {str(e)}")


def format_query_results(sql_query, columns, rows):
    """Format SQL query results as markdown table"""
    if not rows:
        return f"**SQL Query:**\n```sql\n{sql_query}\n```\n\n**Result:** No data found."

    result_text = f"**SQL Query:**\n```sql\n{sql_query}\n```\n\n**Results:**\n\n"
    result_text += "| " + " | ".join(columns) + " |\n"
    result_text += "|" + "---|" * len(columns) + "\n"

    for row in rows:
        result_text += "| " + " | ".join(str(val) for val in row) + " |\n"

    result_text += f"\n📊 *Found {len(rows)} row(s)*"

    return result_text


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


def generate_response(user_message):
    try:
        # CSV Q&A mode
        if st.session_state.get("csv_info"):
            csv_info = st.session_state["csv_info"]
            sql_query = generate_sql_query(user_message, csv_info["schema"])
            query_result = db_utils.execute_csv_query(csv_info["path"], sql_query)

            if query_result["success"]:
                response_text = format_query_results(
                    sql_query,
                    query_result["columns"],
                    query_result["rows"]
                )
                return response_text
            else:
                return f"❌ Query execution failed: {query_result['error']}\n\n**Generated SQL:**\n```sql\n{sql_query}\n```"

        # Regular chat mode
        chat = get_or_create_chat_session(
            st.session_state["session_id"],
            st.session_state["system_prompt"]
        )

        message_parts = [user_message]

        if st.session_state["file_context"]:
            message_parts.append(st.session_state["file_context"])

        # Only add image if using vision mode
        if st.session_state["image_data"] and st.session_state.get("image_processing_mode") == "vision":
            message_parts.append(st.session_state["image_data"])

        response = chat.send_message(message_parts)

        return response.text

    except Exception as e:
        error_message = f"⚠️ Gemini API Error: {str(e)}"
        st.error(error_message)
        raise Exception(error_message)


def handle_user_input(prompt):
    has_attachment = st.session_state["uploaded_file"] is not None
    attachment_name = st.session_state["uploaded_file"].name if has_attachment else ""

    user_message = prompt
    if has_attachment:
        user_message = f"[Attached: {attachment_name}]\n{prompt}"

    try:
        # Generate assistant response FIRST
        assistant_response = generate_response(prompt)

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

        # Clear attachments
        st.session_state["uploaded_file"] = None
        st.session_state["file_context"] = ""
        st.session_state["image_data"] = None
        st.session_state["csv_info"] = None
        st.session_state["audio_transcription"] = None
        st.session_state["ocr_result"] = None

        # Clear messages to force reload
        if "messages" in st.session_state:
            del st.session_state["messages"]

        st.rerun()

    except Exception as e:
        st.error(f"Failed to generate response. Nothing was saved to database.")
        st.session_state["uploaded_file"] = None
        st.session_state["file_context"] = ""
        st.session_state["image_data"] = None
        st.session_state["csv_info"] = None
        st.session_state["audio_transcription"] = None
        st.session_state["ocr_result"] = None
        st.stop()


# ============================================================================
# MAIN APP
# ============================================================================

initialize_session()
display_sidebar()

st.title("💬 Gemini + DuckDB + OCR + Whisper Chat")

display_chat_history()
display_file_uploader()
display_voice_input()

# Chat input - use transcribed text if available, otherwise manual input
if st.session_state.get("transcribed_text"):
    prompt = st.session_state["transcribed_text"]
    st.session_state["transcribed_text"] = ""
    handle_user_input(prompt)
elif prompt := st.chat_input("Type your message here..."):
    handle_user_input(prompt)
