import os
import sqlite3
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from transformers import pipeline

# Load Slack Bot Token securely
SLACK_BOT_TOKEN ="xoxb-8497485985891-8494927306197-YWinmCEXrlbf2oz2N7I9TLw3"
client = WebClient(token=SLACK_BOT_TOKEN)
channel_id = "C08EEFMDZEJ"

# Database Setup
DB_FILE = "slack_summaries.db"

def setup_database():
    """Create the database table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT,
            summary TEXT,
            action_points TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_to_database(channel_id, summary, action_points):
    """Save the summary and action points into SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO summaries (channel_id, summary, action_points) VALUES (?, ?, ?)", 
                   (channel_id, summary, "\n".join(action_points)))
    conn.commit()
    conn.close()

def fetch_messages():
    """Fetch last 30 messages from Slack (adjustable)."""
    try:
        response = client.conversations_history(channel=channel_id, limit=30)
        return [msg["text"] for msg in response["messages"] if msg.get("subtype") != "bot_message"]
    except SlackApiError as e:
        print(f"Error fetching messages: {e.response['error']}")
        return []

def chunk_text(text, chunk_size=512, overlap=100):
    """Split long text into manageable chunks with overlap."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        if len(chunk) < chunk_size:
            break
    return chunks

def extract_action_items(messages):
    """Extract action points using keyword filtering."""
    keywords = ["action", "next steps", "deadline", "task", "follow-up", "todo", "assign"]
    return [msg for msg in messages if any(keyword in msg.lower() for keyword in keywords)]

def summarize_text(text):
    """Summarize the Slack conversation using a pre-trained model."""
    summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
    
    # Handle large texts by breaking them into chunks
    text_chunks = chunk_text(text)
    summaries = [summarizer(chunk, max_length=100, min_length=30, do_sample=False)[0]["summary_text"] for chunk in text_chunks]
    
    return " ".join(summaries)

def main():
    setup_database()
    
    messages = fetch_messages()
    if not messages:
        print("No user messages found.")
        return

    conversation_text = " ".join(messages)

    summary = summarize_text(conversation_text)
    action_items = extract_action_items(messages)

    # Save to database
    save_to_database(channel_id, summary, action_items)

    # Prepare message to send to Slack
    summary_message = f"📢 *Summary of Key Conversations:* \n\n{summary}"
    if action_items:
        summary_message += "\n\n📌 *Action Points:*"
        for i, action in enumerate(action_items, 1):
            summary_message += f"\n{i}. {action}"

    # Send summary to Slack
    client.chat_postMessage(channel=channel_id, text=summary_message)
    print("✅ Summary sent to Slack successfully!")

if __name__ == "__main__":
    main()
