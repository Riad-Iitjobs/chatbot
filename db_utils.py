import duckdb


connection = duckdb.connect('local_chat.db')


connection.execute("CREATE TABLE IF NOT EXISTS chats (session_id VARCHAR, timestamp TIMESTAMP, role VARCHAR CHECK (role IN ('user', 'assistant')),content_text VARCHAR, has_attachment BOOLEAN  )")

# session_id (VARCHAR)
# timestamp (TIMESTAMP)
# role (VARCHAR) → only user or assistant
# content_text (VARCHAR)
# has_attachment (BOOLEAN)

def get_db_connection():
    try:
        return connection
    except Exception as e:
        print(f"Error getting database connection: {e}")
        raise e


def save_message(session_id, timestamp, role, content_text, has_attachment):
    connection = get_db_connection()
    connection.execute( "INSERT INTO chats VALUES (?, ?, ?, ?, ?)",(session_id, timestamp, role, content_text, has_attachment))

def load_history(session_id):
    connection = get_db_connection()
    return connection.execute("SELECT * from chats where session_id = ? ORDER BY timestamp", (session_id,)).fetchall()



def try_message_insert(session_id, timestamp, role, content_text, has_attachment):
    try:
        save_message(session_id, timestamp, role, content_text, has_attachment)
    except Exception as e:
        print(f"Error saving message: {e}")
        raise e





def get_all_sessions():
    """Get list of all unique session IDs"""
    connection = get_db_connection()
    result = connection.execute(
        "SELECT DISTINCT session_id FROM chats ORDER BY session_id"
    ).fetchall()
    return [row[0] for row in result]



# def get_single_conversation(session_id):
#     connection=get_db_connection()
#     result = connection.execute("Select * from chats where session_id = ")