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
def generate_sql_query(user_question, csv_schema):
    """Generate SQL query using Gemini for CSV Q&A"""
    try:
        # Format schema for prompt
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

        # Remove markdown code blocks if present
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

        return sql_query

    except Exception as e:
        raise Exception(f"Failed to generate SQL: {str(e)}")


def format_query_results(sql_query, columns, rows):
    """Format SQL query results as markdown table"""
    if not rows:
        return f"**SQL Query:**\n```sql\n{sql_query}\n```\n\n**Result:** No data found."

    # Create markdown table
    result_text = f"**SQL Query:**\n```sql\n{sql_query}\n```\n\n**Results:**\n\n"
    result_text += "| " + " | ".join(columns) + " |\n"
    result_text += "|" + "---|" * len(columns) + "\n"

    for row in rows:
        result_text += "| " + " | ".join(str(val) for val in row) + " |\n"

    result_text += f"\n📊 *Found {len(rows)} row(s)*"

    return result_text


def generate_response(user_message):
    try:
        # Check if CSV Q&A mode is active
        if st.session_state.get("csv_info"):
            csv_info = st.session_state["csv_info"]

            # Generate SQL query
            sql_query = generate_sql_query(user_message, csv_info["schema"])

            # Execute query
            query_result = db_utils.execute_csv_query(csv_info["path"], sql_query)

            if query_result["success"]:
                # Format results
                response_text = format_query_results(
                    sql_query,
                    query_result["columns"],
                    query_result["rows"]
                )
                return response_text
            else:
                return f"❌ Query execution failed: {query_result['error']}\n\n**Generated SQL:**\n```sql\n{sql_query}\n```"

        # Regular chat mode (non-CSV)
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

    except Exception as e:
        error_message = f"⚠️ Gemini API Error: {str(e)}"
        st.error(error_message)
        raise Exception(error_message)


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

# Voice input interface
app_ui.display_voice_input()

# Chat input - use transcribed text if available, otherwise manual input
if st.session_state.get("transcribed_text"):
    # Auto-submit transcribed text
    prompt = st.session_state["transcribed_text"]
    st.session_state["transcribed_text"] = ""  # Clear after using
    app_ui.handle_user_input(prompt, generate_response)
elif prompt := st.chat_input("Type your message here..."):
    app_ui.handle_user_input(prompt, generate_response)



