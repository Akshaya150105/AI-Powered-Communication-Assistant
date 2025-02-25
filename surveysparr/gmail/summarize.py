from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
import email
from transformers import pipeline
from bs4 import BeautifulSoup

# Set up API Scope
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def authenticate_gmail():
    """Authenticate and return the Gmail API service."""
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=8080)  # Ensure this port is registered in Google Cloud Console
    
    # Build Gmail API service
    service = build("gmail", "v1", credentials=creds)
    return service

def list_messages(service, user_id="me", max_results=5):
    """Fetches latest email messages and extracts their body content."""
    try:
        results = service.users().messages().list(userId=user_id, maxResults=max_results).execute()
        messages = results.get("messages", [])

        if not messages:
            print("No messages found.")
            return

        for msg in messages:
            message = service.users().messages().get(userId=user_id, id=msg["id"]).execute()
            payload = message["payload"]
            headers = payload["headers"]

            # Extract subject
            subject = next((header["value"] for header in headers if header["name"] == "Subject"), "No Subject")
            print(f"📩 Email Subject: {subject}")

            # Extract sender
            sender = next((header["value"] for header in headers if header["name"] == "From"), "Unknown Sender")
            print(f"📨 From: {sender}")

            # Extract and decode email body
            body = get_email_body(payload)
            print(f"📜 Email Body:\n{body[:500]}...")  # Print first 500 characters

            # Summarize email body
            if body.strip():
                summary = summarize_text(body)
                print(f"🔍 Summary:\n{summary}")
            else:
                print("🔍 Summary: [No Text Content]")
            print("-" * 50)

    except Exception as e:
        print(f"An error occurred: {e}")

def get_email_body(payload):
    """Extracts the email body, handling both plain text and HTML."""
    
    if "parts" in payload:
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")

            if mime_type == "text/plain" and "data" in part["body"]:  
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")

            elif mime_type == "text/html" and "data" in part["body"]:  
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")

            elif "parts" in part:  # Recursive call for deeply nested emails
                return get_email_body(part)

    elif "body" in payload and "data" in payload["body"]:
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

    return "[No Text Content]"

def clean_text(text):
    """Removes HTML tags and excessive whitespace."""
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ").strip()

def summarize_text(text):
    """Summarizes long text by splitting it into chunks and summarizing each separately."""
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

    # Clean HTML if needed
    text = clean_text(text)

    max_chunk_size = 1024  # Reduce to avoid token overflow
    overlap = 100  # Ensures context continuity in summaries
    
    if len(text) > max_chunk_size:
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + max_chunk_size
            chunk = text[start:end]

            # Ensure we don’t cut words abruptly
            if end < len(text):
                last_space = chunk.rfind(" ")
                if last_space != -1:
                    end = start + last_space
                    chunk = text[start:end]

            chunks.append(chunk.strip())
            start = end - overlap  # Maintain slight overlap between chunks
        
        summaries = [summarizer(chunk, max_length=130, min_length=30, do_sample=False)[0]['summary_text'] for chunk in chunks]
        return " ".join(summaries)
    else:
        summary = summarizer(text, max_length=130, min_length=30, do_sample=False)
        return summary[0]['summary_text']

if __name__ == "__main__":
    gmail_service = authenticate_gmail()
    list_messages(gmail_service, max_results=5)  # Fetch latest 5 emails