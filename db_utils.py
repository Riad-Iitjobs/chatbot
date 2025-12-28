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


def get_csv_schema(csv_path):
    """Get schema (columns and types) from CSV file using DuckDB"""
    try:
        connection = get_db_connection()
        result = connection.execute(
            f"DESCRIBE SELECT * FROM read_csv_auto('{csv_path}')"
        ).fetchall()

        # Extract column name and type
        schema = []
        for row in result:
            column_name = row[0]
            data_type = row[1]
            schema.append({
                "name": column_name,
                "type": data_type
            })

        return {
            "success": True,
            "schema": schema
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def execute_csv_query(csv_path, sql_query):
    """Execute SQL query on CSV file using DuckDB"""
    try:
        connection = get_db_connection()

        # Replace csv_data placeholder with actual CSV read
        full_query = sql_query.replace(
            "FROM csv_data",
            f"FROM read_csv_auto('{csv_path}')"
        )

        # Execute query
        result = connection.execute(full_query).fetchall()

        # Get column names
        columns = [desc[0] for desc in connection.description]

        return {
            "success": True,
            "columns": columns,
            "rows": result,
            "row_count": len(result)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# def get_single_conversation(session_id):
#     connection=get_db_connection()
#     result = connection.execute("Select * from chats where session_id = ")