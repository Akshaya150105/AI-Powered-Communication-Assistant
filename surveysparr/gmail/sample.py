from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
import email

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

if __name__ == "__main__":
    gmail_service = authenticate_gmail()
    list_messages(gmail_service, max_results=5)  # Fetch latest 5 emails
