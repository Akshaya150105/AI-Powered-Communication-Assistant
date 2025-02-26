import os
import sqlite3
import faiss
import numpy as np
import streamlit as st
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from transformers import AutoTokenizer, AutoModel
import torch
import pandas as pd

# Set page configuration
st.set_page_config(
    page_title="Slack Search Tool",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database Setup
DB_FILE = "slack_search_channel.db"

# Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #4A154B;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #36C5F0;
        margin-bottom: 1rem;
    }
    .message-box {
        background-color: #f9f9f9;
        border-left: 5px solid #4A154B;
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 0.5rem;
    }
    .file-box {
        background-color: #f1f2f6;
        border-left: 5px solid #36C5F0;
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 0.5rem;
    }
    .channel-name {
        color: #4A154B;
        font-weight: bold;
    }
    .timestamp {
        color: #888;
        font-size: 0.8rem;
    }
    .loader {
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Functions from the original code
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
            text TEXT,
            timestamp TEXT,
            UNIQUE(channel_id, text) ON CONFLICT REPLACE
        )
    """)
    
    # Files table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT,
            channel_name TEXT,
            user TEXT,
            file_id TEXT UNIQUE,
            file_name TEXT,
            file_url TEXT,
            timestamp TEXT
        )
    """)
    
    conn.commit()
    conn.close()

def get_channel_id(client, channel_name):
    """Fetch the ID of a channel by name."""
    try:
        response = client.conversations_list()
        if response["ok"]:
            for channel in response["channels"]:
                if channel["name"] == channel_name:
                    return channel["id"]
        return None
    except SlackApiError as e:
        st.error(f"Slack API Error: {e.response['error']}")
        return None

def fetch_messages(client, channel_id, channel_name, limit=100):
    """Fetch latest messages and files from Slack and store them."""
    try:
        response = client.conversations_history(channel=channel_id, limit=limit)
        messages = []
        files = []

        for msg in response["messages"]:
            if msg.get("subtype") != "bot_message" and "text" in msg and msg["text"].strip():
                messages.append((channel_id, channel_name, msg.get("user", "unknown"), msg["text"], datetime.fromtimestamp(float(msg["ts"]))))
                
                # If message contains files, store them
                if "files" in msg:
                    for file in msg["files"]:
                        file_url = file.get("url_private", "")
                        files.append((channel_id, channel_name, msg.get("user", "unknown"), file["id"], file["name"], file_url, datetime.fromtimestamp(float(msg["ts"]))))

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Store messages
        for message in messages:
            try:
                cursor.execute(
                    "INSERT OR REPLACE INTO messages (channel_id, channel_name, user, text, timestamp) VALUES (?, ?, ?, ?, ?)",
                    message
                )
            except sqlite3.IntegrityError:
                # Skip duplicate messages
                pass

        # Store files
        for file in files:
            channel_id, channel_name, user, file_id, file_name, file_url, timestamp = file
            try:
                cursor.execute(
                    "INSERT OR REPLACE INTO files (channel_id, channel_name, user, file_id, file_name, file_url, timestamp) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (channel_id, channel_name, user, file_id, file_name, file_url, timestamp)
                )
            except sqlite3.IntegrityError:
                # Skip duplicate files
                pass

        conn.commit()
        conn.close()

        return len(messages), len(files)
    
    except SlackApiError as e:
        st.error(f"Error fetching messages for {channel_name}: {e.response['error']}")
        return 0, 0

@st.cache_resource
def load_model():
    """Load and cache the model and tokenizer."""
    tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    return tokenizer, model

def encode_text(texts):
    """Convert text into embeddings."""
    tokenizer, model = load_model()
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
        return None, None

    messages = [row[1] for row in data]
    ids = [row[0] for row in data]

    embeddings = encode_text(messages)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(np.array(embeddings, dtype=np.float32))

    return index, ids

def search_messages(query, top_k=5):
    """Search for messages based on user query."""
    with st.spinner("Searching messages..."):
        index, ids = build_faiss_index()

        if index is None or ids is None:
            return []

        query_embedding = encode_text([query])
        D, I = index.search(np.array(query_embedding, dtype=np.float32), top_k)

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        results = []
        # Keep track of messages we've already added to results
        seen_messages = set()

        # Search messages
        for idx in I[0]:
            if idx == -1 or idx >= len(ids):  # Ensure index is valid
                continue
            
            cursor.execute("SELECT text, timestamp, channel_name, user FROM messages WHERE id = ?", (ids[idx],))
            row = cursor.fetchone()

            if row:
                msg, timestamp, channel_name, user = row
                if msg.strip():  # Ensure message is not empty
                    # Create a unique identifier for this message
                    message_id = f"{channel_name}_{user}_{msg}"
                    
                    # Only add if we haven't seen this message yet
                    if message_id not in seen_messages:
                        seen_messages.add(message_id)
                        results.append({
                            "type": "message",
                            "content": msg,
                            "timestamp": timestamp,
                            "channel": channel_name,
                            "user": user
                        })

        conn.close()
        return results

def search_files(query):
    """Find files based on name or extension."""
    with st.spinner("Searching files..."):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT channel_name, file_name, file_url, timestamp, user, file_id 
            FROM files 
            WHERE file_name LIKE ? OR file_name LIKE ?
        """, ('%' + query + '%', '%.' + query))  # Allows searching by name or extension (e.g., "pdf")

        results = cursor.fetchall()
        conn.close()

        # Use a set to track unique file IDs
        seen_files = set()
        unique_results = []
        
        for channel, name, url, timestamp, user, file_id in results:
            if file_id not in seen_files:
                seen_files.add(file_id)
                unique_results.append({
                    "type": "file",
                    "channel": channel,
                    "name": name,
                    "url": url,
                    "timestamp": timestamp,
                    "user": user
                })
        
        return unique_results

def get_all_channels():
    """Get all channel names from the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT channel_name FROM messages")
    channels = cursor.fetchall()
    conn.close()
    return [channel[0] for channel in channels]

def get_statistics():
    """Get database statistics."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM messages")
    message_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM files")
    file_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT channel_name) FROM messages")
    channel_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "messages": message_count,
        "files": file_count,
        "channels": channel_count
    }

# Main application
def main():
    setup_database()
    
    # Header
    st.markdown('<div class="main-header">🔍 Slack Search Tool</div>', unsafe_allow_html=True)
    
    # Sidebar for controls
    with st.sidebar:
        st.markdown('<div class="sub-header">Settings</div>', unsafe_allow_html=True)
        
        # Slack token input
        slack_token = st.text_input("Enter Slack Bot Token", type="password", value="xoxb-8497485985891-8494927306197-YWinmCEXrlbf2oz2N7I9TLw3")
        
        # Initialize client if token is provided
        client = None
        if slack_token:
            client = WebClient(token=slack_token)
        
        st.markdown('<div class="sub-header">Channel Management</div>', unsafe_allow_html=True)
        
        # Channel input
        channel_input = st.text_input("Enter channel names (comma-separated)")
        
        # Fetch button
        if st.button("Fetch Channel Data"):
            if not client:
                st.error("Please provide a valid Slack token first.")
            elif not channel_input:
                st.error("Please enter at least one channel name.")
            else:
                channel_names = [c.strip() for c in channel_input.split(",")]
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                total_messages = 0
                total_files = 0
                
                for i, channel_name in enumerate(channel_names):
                    status_text.text(f"Processing #{channel_name}...")
                    channel_id = get_channel_id(client, channel_name)
                    
                    if channel_id:
                        msg_count, file_count = fetch_messages(client, channel_id, channel_name)
                        total_messages += msg_count
                        total_files += file_count
                    else:
                        st.warning(f"Channel '{channel_name}' not found.")
                    
                    progress_bar.progress((i + 1) / len(channel_names))
                
                status_text.text(f"✅ Fetched {total_messages} messages and {total_files} files from {len(channel_names)} channels.")
        
        # Statistics section
        st.markdown('<div class="sub-header">Database Statistics</div>', unsafe_allow_html=True)
        stats = get_statistics()
        
        st.metric("Indexed Messages", stats["messages"])
        st.metric("Stored Files", stats["files"])
        st.metric("Channels", stats["channels"])
        
        # Database reset option
        st.markdown('<div class="sub-header">Database Management</div>', unsafe_allow_html=True)
        if st.button("Clear Database", type="primary"):
            if st.session_state.get("confirm_clear", False):
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM messages")
                cursor.execute("DELETE FROM files")
                conn.commit()
                conn.close()
                st.success("Database cleared successfully!")
                st.session_state["confirm_clear"] = False
            else:
                st.session_state["confirm_clear"] = True
                st.warning("Are you sure? Click again to confirm.")
        else:
            st.session_state["confirm_clear"] = False
    
    # Main content area - Tabs
    tab1, tab2, tab3 = st.tabs(["Search", "Explore Channels", "About"])
    
    # Search Tab
    with tab1:
        st.markdown('<div class="sub-header">Search Slack Content</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            query = st.text_input("Enter your search query")
        
        with col2:
            search_type = st.selectbox("Search type", ["All", "Messages Only", "Files Only"])
            top_k = st.slider("Results to show", 3, 20, 5)
        
        if st.button("Search") and query:
            # Initialize results
            message_results = []
            file_results = []
            
            # Perform search based on type
            if search_type in ["All", "Messages Only"]:
                message_results = search_messages(query, top_k=top_k)
            
            if search_type in ["All", "Files Only"]:
                file_results = search_files(query)
            
            # Display results
            all_results = message_results + file_results
            
            if all_results:
                st.markdown(f"### Found {len(all_results)} results")
                
                # Sort results by timestamp
                all_results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                
                for result in all_results:
                    if result["type"] == "message":
                        st.markdown(f'''
                        <div class="message-box">
                            <span class="channel-name">#{result["channel"]}</span> • <span class="timestamp">{result["timestamp"]}</span><br>
                            <strong>User:</strong> {result["user"]}<br>
                            {result["content"]}
                        </div>
                        ''', unsafe_allow_html=True)
                    else:  # File result
                        st.markdown(f'''
                        <div class="file-box">
                            <span class="channel-name">#{result["channel"]}</span> • <span class="timestamp">{result["timestamp"]}</span><br>
                            <strong>User:</strong> {result["user"]}<br>
                            📂 <strong>{result["name"]}</strong><br>
                            <a href="{result["url"]}" target="_blank">Download File</a>
                        </div>
                        ''', unsafe_allow_html=True)
            else:
                st.info("No results found. Try a different search query or fetch more channel data.")
    
    # Explore Tab
    with tab2:
        st.markdown('<div class="sub-header">Explore Channel Content</div>', unsafe_allow_html=True)
        
        channels = get_all_channels()
        if channels:
            selected_channel = st.selectbox("Select a channel", channels)
            
            if selected_channel:
                # Show messages from the selected channel
                conn = sqlite3.connect(DB_FILE)
                df_messages = pd.read_sql(f"SELECT text, timestamp, user FROM messages WHERE channel_name = '{selected_channel}' ORDER BY timestamp DESC LIMIT 50", conn)
                df_files = pd.read_sql(f"SELECT file_name, file_url, timestamp, user FROM files WHERE channel_name = '{selected_channel}' ORDER BY timestamp DESC", conn)
                conn.close()
                
                # Show message and file counts
                st.markdown(f"### {len(df_messages)} messages, {len(df_files)} files")
                
                # Messages
                if not df_messages.empty:
                    st.markdown("#### Recent Messages")
                    for i, row in df_messages.iterrows():
                        st.markdown(f'''
                        <div class="message-box">
                            <span class="timestamp">{row['timestamp']}</span><br>
                            <strong>User:</strong> {row['user']}<br>
                            {row['text']}
                        </div>
                        ''', unsafe_allow_html=True)
                
                # Files
                if not df_files.empty:
                    st.markdown("#### Files")
                    for i, row in df_files.iterrows():
                        st.markdown(f'''
                        <div class="file-box">
                            <span class="timestamp">{row['timestamp']}</span><br>
                            <strong>User:</strong> {row['user']}<br>
                            📂 <strong>{row['file_name']}</strong><br>
                            <a href="{row['file_url']}" target="_blank">Download File</a>
                        </div>
                        ''', unsafe_allow_html=True)
        else:
            st.info("No channels found. Fetch some channel data first.")
    
    # About Tab
    with tab3:
        st.markdown('<div class="sub-header">About This App</div>', unsafe_allow_html=True)
        
        st.markdown("""
        This Slack Search Tool allows you to:
        
        1. **Fetch and index** messages and files from multiple Slack channels
        2. **Search content** using natural language processing
        3. **Explore channels** to browse recent messages and files
        
        ### How It Works
        
        - Messages are indexed using sentence transformers and FAISS for semantic search
        - Files are searched by filename and extension
        - All data is stored locally in a SQLite database
        
        ### Tips for Better Search
        
        - Be specific with your search terms
        - For file searches, you can search by file extension (e.g., "pdf", "xlsx")
        - Fetch data from relevant channels for better results
        """)

if __name__ == "__main__":
    main()