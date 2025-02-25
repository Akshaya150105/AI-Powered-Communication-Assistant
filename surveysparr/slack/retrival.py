import os
import sqlite3
import faiss
import numpy as np
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from transformers import AutoTokenizer, AutoModel
import torch

# Load environment variables
SLACK_BOT_TOKEN = "xoxb-8497485985891-8494927306197-YWinmCEXrlbf2oz2N7I9TLw3"
client = WebClient(token=SLACK_BOT_TOKEN)

# Database Setup
DB_FILE = "slack_search_channel.db"

def setup_database():
    """Create the database tables if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT,
            channel_name TEXT,
            user TEXT,
            text TEXT UNIQUE,
            timestamp TEXT
        )
    """)
    
    # Files table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT,
            channel_name TEXT,
            user TEXT,
            file_id TEXT,
            file_name TEXT,
            file_url TEXT,
            timestamp TEXT
        )
    """)
    
    conn.commit()
    conn.close()

def get_channel_id(channel_name):
    """Fetch the ID of a channel by name."""
    try:
        response = client.conversations_list()
        if response["ok"]:
            for channel in response["channels"]:
                if channel["name"] == channel_name:
                    return channel["id"]
        print(f"❌ Channel '{channel_name}' not found.")
    except SlackApiError as e:
        print(f"Slack API Error: {e.response['error']}")
    return None

def fetch_messages(channel_id, channel_name, limit=100):
    """Fetch latest messages and files from Slack and store them."""
    try:
        response = client.conversations_history(channel=channel_id, limit=limit)
        messages = []
        files = []

        for msg in response["messages"]:
            if msg.get("subtype") != "bot_message":
                messages.append((channel_id, channel_name, msg.get("user", "unknown"), msg["text"], datetime.fromtimestamp(float(msg["ts"]))))
                
                # Debug: Print message content
                print(f"📥 Processing Message: {msg['text']}")

                # If message contains files, store them
                if "files" in msg:
                    for file in msg["files"]:
                        file_url = file["url_private"]
                        print(f"📎 Found File: {file['name']} (URL: {file_url})")  # Debug print

                        files.append((channel_id, channel_name, msg.get("user", "unknown"), file["id"], file["name"], file_url, datetime.fromtimestamp(float(msg["ts"]))))

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Store messages
        if messages:
            cursor.executemany("INSERT INTO messages (channel_id, channel_name, user, text, timestamp) VALUES (?, ?, ?, ?, ?)", messages)

        # Store files
        if files:
            for file in files:
                channel_id, channel_name, user, file_id, file_name, file_url, timestamp = file

                # 🔍 Check if the file ID already exists
                cursor.execute("SELECT COUNT(*) FROM files WHERE file_id = ?", (file_id,))
                file_exists = cursor.fetchone()[0]

                if file_exists == 0:  # ✅ Only insert if the file is new
                    cursor.execute(
                        "INSERT INTO files (channel_id, channel_name, user, file_id, file_name, file_url, timestamp) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (channel_id, channel_name, user, file_id, file_name, file_url, timestamp)
                    )
                else:
                    print(f"🔄 Skipping duplicate file: {file_name} (ID: {file_id})") 

        conn.commit()
        conn.close()

        print(f"✅ {len(messages)} messages and {len(files)} files stored for #{channel_name}.")
    
    except SlackApiError as e:
        print(f"❌ Error fetching messages for {channel_name}: {e.response['error']}")

def encode_text(texts):
    """Convert text into embeddings."""
    tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    inputs = tokenizer(texts, padding=True, truncation=True, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state[:, 0, :].numpy()

def build_faiss_index():
    """Index stored messages for fast retrieval."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, text FROM messages")
    data = cursor.fetchall()
    conn.close()

    if not data:
        print("No messages to index.")
        return None, None

    messages = [row[1] for row in data]
    ids = [row[0] for row in data]

    embeddings = encode_text(messages)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(np.array(embeddings, dtype=np.float32))

    return index, ids

def search_messages(query, top_k=5):
    """Search for messages and files based on user query."""
    index, ids = build_faiss_index()

    if index is None or ids is None:
        return "❌ No messages indexed yet."

    query_embedding = encode_text([query])
    D, I = index.search(np.array(query_embedding, dtype=np.float32), top_k)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    results = []

    # 🔍 Search messages
    for idx in I[0]:
        if idx == -1 or idx >= len(ids):  # Ensure index is valid
            continue
        
        cursor.execute("SELECT text, timestamp, channel_name FROM messages WHERE id = ?", (ids[idx],))
        row = cursor.fetchone()

        if row:
            msg, timestamp, channel_name = row
            if msg.strip():  # Ensure message is not empty
                results.append(f"📌 *Channel: #{channel_name}*\n📢 *Message:* {msg}  \n🕒 *Date:* {timestamp}")

    # 🔍 Search files separately (since FAISS doesn't index them)
    cursor.execute("SELECT file_name, file_url, channel_name FROM files WHERE file_name LIKE ?", (f"%{query}%",))
    file_results = cursor.fetchall()

    for file_name, file_url, channel_name in file_results:
        results.append(f"📂 *File:* {file_name}  \n🔗 *URL:* {file_url}  \n📌 *Channel: #{channel_name}*")

    conn.close()

    return "\n\n".join(results) if results else "❌ No relevant messages or files found."


def search_files(query):
    """Find files based on name or extension."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT channel_name, file_name, file_url 
        FROM files 
        WHERE file_name LIKE ? OR file_name LIKE ?
    """, ('%' + query + '%', '%.' + query))  # Allows searching by name or extension (e.g., "pdf")

    results = cursor.fetchall()
    conn.close()

    if not results:
        return "❌ No matching files found."

    return "\n\n".join([
        f"📌 *Channel: #{channel}*\n📂 *File:* {name}  \n🔗 [Download File]({url})"
        for channel, name, url in results
    ])


def handle_query(query):
    """Determine if the query is for messages or files."""
    if "file" in query.lower() or "." in query:  # Detect file-related searches
        return search_files(query.strip())
    return search_messages(query)

def main():
    setup_database()
    
    # Get user input for channels
    channel_names = input("Enter channel names (comma-separated): ").split(",")
    
    # Process each channel
    for channel_name in channel_names:
        channel_name = channel_name.strip()
        channel_id = get_channel_id(channel_name)

        if channel_id:
            fetch_messages(channel_id, channel_name)

    # Example Queries
    query = input("\n🔍 Enter a search query: ")
    print("\n🔍 Search Results:")
    print(handle_query(query))

if __name__ == "__main__":
    main()
