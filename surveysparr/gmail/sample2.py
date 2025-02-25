import sqlite3
import base64
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Set up API Scope
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def authenticate_gmail():
    """Authenticate and return the Gmail API service."""
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=8080)  
    return build("gmail", "v1", credentials=creds)

def list_messages(service, user_id="me", max_results=50):
    """Fetches latest email messages, extracts sender, receiver, subject, and clean body, and stores in SQLite."""
    try:
        results = service.users().messages().list(userId=user_id, maxResults=max_results).execute()
        messages = results.get("messages", [])

        if not messages:
            print("No messages found.")
            return

        email_data = []  # List to store email details

        for msg in messages:
            message = service.users().messages().get(userId=user_id, id=msg["id"]).execute()
            payload = message.get("payload", {})
            headers = payload.get("headers", [])

            # Extract sender
            sender = next((header["value"] for header in headers if header["name"] == "From"), "Unknown Sender")
            
            # Extract receiver
            receiver = next((header["value"] for header in headers if header["name"] == "To"), "Unknown Receiver")

            # Extract subject
            subject = next((header["value"] for header in headers if header["name"] == "Subject"), "No Subject")

            # Extract and clean email body
            body = get_email_body(payload)

            # Filter out empty or invalid emails
            if body.strip() and sender != "Unknown Sender":
                email_data.append((sender, receiver, subject, body[:500]))  # Store first 500 characters of body

        # Save to SQLite database
        save_to_sqlite(email_data)

    except Exception as e:
        print(f"An error occurred: {e}")


def get_email_body(payload):
    """Extracts the email body, handling both plain text and HTML, and removes unwanted tags."""
    if "parts" in payload:
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")

            if mime_type == "text/plain" and "data" in part["body"]:  
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8").strip()

            elif mime_type == "text/html" and "data" in part["body"]:  
                raw_html = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                return clean_html(raw_html)  # Clean the extracted HTML

            elif "parts" in part:  # Recursive call for deeply nested emails
                return get_email_body(part)

    elif "body" in payload and "data" in payload["body"]:
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8").strip()

    return "[No Text Content]"

def clean_html(html):
    """Removes HTML tags and extracts readable text."""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ").strip()

def save_to_sqlite(email_data, db_name="emails.db"):
    """Saves extracted email data to an SQLite database, including the subject."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Update table schema to include subject
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            receiver TEXT,
            subject TEXT,  -- Added subject column
            email_body TEXT
        )
    """)

    # Insert email data including subject
    cursor.executemany("INSERT INTO emails (sender, receiver, subject, email_body) VALUES (?, ?, ?, ?)", email_data)

    conn.commit()
    conn.close()
    print(f"✅ Emails saved to {db_name} database.")


if __name__ == "__main__":
    gmail_service = authenticate_gmail()
    list_messages(gmail_service, max_results=100)
