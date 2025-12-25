import db as db_utils
from datetime import datetime
# first im checking the db cooncetion 
db_conncection = db_utils.get_db_connection()

print(db_conncection)

session_id = 2
timestamp = datetime.now()
has_attachment = False
insert_try= db_utils.try_message_insert(session_id, timestamp, "user", "Hello, how are you?", has_attachment)
insert_try= db_utils.try_message_insert(session_id, timestamp, "assistant", "Hello,im good, what about you?", has_attachment)



getting_history = db_utils.load_history(session_id)
print(getting_history)