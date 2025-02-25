from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from transformers import pipeline
import os
import re
import sqlite3
# Load Slack Bot Token securely
SLACK_BOT_TOKEN ="xoxb-8497485985891-8494927306197-YWinmCEXrlbf2oz2N7I9TLw3"
client = WebClient(token=SLACK_BOT_TOKEN)
channel_id = "C08EEFMDZEJ"
DB_FILE = "slack_tasks.db"

def setup_database():
    """Create the database table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT,
            task_description TEXT,
            assignee TEXT,
            due_date TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_task(channel_id, task_description, assignee, due_date):
    """Save identified tasks into the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (channel_id, task_description, assignee, due_date) VALUES (?, ?, ?, ?)", 
                   (channel_id, task_description, assignee, due_date))
    conn.commit()
    conn.close()

def fetch_messages():
    """Fetch last 30 messages from Slack."""
    try:
        response = client.conversations_history(channel=channel_id, limit=30)
        return [msg["text"] for msg in response["messages"] if msg.get("subtype") != "bot_message"]
    except SlackApiError as e:
        print(f"Error fetching messages: {e.response['error']}")
        return []

def extract_tasks(messages):
    """Extract actionable tasks from Slack messages."""
    task_keywords = ["assign", "deadline", "follow up", "complete by", "due", "finish", "review", "submit"]
    due_date_pattern = r"\b(by|before|due)\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|\d{1,2}(st|nd|rd|th)?\s+\w+|\d{1,2}/\d{1,2}/\d{2,4})\b"
    mention_pattern = r"@(\w+)"  # Slack mentions

    tasks = []
    for msg in messages:
        if any(keyword in msg.lower() for keyword in task_keywords):
            task_desc = msg  # Full message as task description
            
            # Extract assignee (@mentions)
            assignees = re.findall(mention_pattern, msg)
            assignee = assignees[0] if assignees else "Unassigned"

            # Extract due date (if mentioned)
            due_date_match = re.search(due_date_pattern, msg)
            due_date = due_date_match.group(0) if due_date_match else "No due date"

            tasks.append({"task": task_desc, "assignee": assignee, "due_date": due_date})
    
    return tasks

def main():
    setup_database()
    
    messages = fetch_messages()
    if not messages:
        print("No user messages found.")
        return

    tasks = extract_tasks(messages)

    if not tasks:
        print("No actionable tasks found.")
        return

    # Save tasks to the database
    for task in tasks:
        save_task(channel_id, task["task"], task["assignee"], task["due_date"])

    # Prepare and send a task summary to Slack
    task_message = "📌 *Identified Tasks:*"
    for i, task in enumerate(tasks, 1):
        task_message += f"\n{i}. **Task:** {task['task']}\n   - **Assignee:** {task['assignee']}\n   - **Due Date:** {task['due_date']}"

    client.chat_postMessage(channel=channel_id, text=task_message)
    print("✅ Tasks extracted and sent to Slack successfully!")

if __name__ == "__main__":
    main()