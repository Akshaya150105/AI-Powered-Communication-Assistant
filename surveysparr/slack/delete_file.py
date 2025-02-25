import sqlite3

DB_FILE = "slack_search_channel.db"  # Database file name

def delete_all_rows(table_name):
    """Delete all rows from a given table."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(f"DELETE FROM files")  # Delete all rows
    conn.commit()
    
    print(f"✅ All rows deleted from files.")
    
    conn.close()

# Example: Delete all rows from the "files" table
delete_all_rows("files")
