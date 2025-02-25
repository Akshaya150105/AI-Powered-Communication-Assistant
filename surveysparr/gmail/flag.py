from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
import email
import time
from datetime import datetime, timedelta

# Set up API Scope
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def authenticate_gmail():
    """Authenticate and return the Gmail API service."""
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=8080)
    
    # Build Gmail API service
    service = build("gmail", "v1", credentials=creds)
    return service

def list_important_unanswered_messages(service, user_id="me", max_results=5):
    """Fetches important unanswered emails and flags them for follow-up."""
    try:
        query = "is:unread is:important -from:me -in:chats"
        results = service.users().messages().list(userId=user_id, maxResults=max_results, q=query).execute()
        messages = results.get("messages", [])

        if not messages:
            print("✅ No unanswered important messages found.")
            return []

        email_data = []
        
        for msg in messages:
            message = service.users().messages().get(userId=user_id, id=msg["id"]).execute()
            payload = message["payload"]
            headers = payload["headers"]

            # Extract subject and sender
            subject = next((header["value"] for header in headers if header["name"] == "Subject"), "No Subject")
            sender = next((header["value"] for header in headers if header["name"] == "From"), "Unknown Sender")

            print(f"📩 Important Unanswered Email: {subject}")
            print(f"📨 From: {sender}")

            # Flag email with a "Pending Reply" label
            add_label(service, msg["id"], "Pending Reply")

            email_data.append({
                "id": msg["id"],
                "subject": subject,
                "sender": sender,
                "timestamp": datetime.now().isoformat(),
            })

        return email_data

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return []

def add_label(service, message_id, label_name):
    """Adds a label to an email (e.g., 'Pending Reply')."""
    try:
        # Fetch existing labels
        labels = service.users().labels().list(userId="me").execute().get("labels", [])
        label_id = next((label["id"] for label in labels if label["name"] == label_name), None)

        # Create label if it doesn't exist
        if not label_id:
            label_obj = {
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }
            created_label = service.users().labels().create(userId="me", body=label_obj).execute()
            label_id = created_label["id"]

        # Add label to email
        msg_labels = {"addLabelIds": [label_id], "removeLabelIds": []}
        service.users().messages().modify(userId="me", id=message_id, body=msg_labels).execute()
        print(f"✅ Email {message_id} flagged as '{label_name}'.")

    except Exception as e:
        print(f"❌ Failed to add label: {e}")

def send_reminder(service, email_data, reminder_hours=24):
    """Sends a reminder email if an important email is unanswered after a set time."""
    try:
        now = datetime.now()
        
        for email_info in email_data:
            email_time = datetime.fromisoformat(email_info["timestamp"])
            time_diff = now - email_time

            if time_diff >= timedelta(hours=reminder_hours):
                subject = f"Reminder: Unanswered Email - {email_info['subject']}"
                body = f"Hi,\n\nThis is a reminder to respond to the email from {email_info['sender']} regarding '{email_info['subject']}'.\n\nBest,\nYour Gmail Assistant"

                send_email(service, "your-email@gmail.com", subject, body)
                print(f"📩 Reminder Sent for: {email_info['subject']}")

    except Exception as e:
        print(f"❌ Error in sending reminder: {e}")

def send_email(service, to_email, subject, body):
    """Sends an email using Gmail API."""
    try:
        message = email.message.EmailMessage()
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"raw": encoded_message}

        service.users().messages().send(userId="me", body=create_message).execute()
        print(f"✅ Reminder email sent to {to_email}")

    except Exception as e:
        print(f"❌ Failed to send email: {e}")

if __name__ == "__main__":
    gmail_service = authenticate_gmail()

    # Fetch and flag important unanswered emails
    unanswered_emails = list_important_unanswered_messages(gmail_service, max_results=5)

    # Wait 24 hours before sending a reminder (for testing, change to minutes)
    time.sleep(5)  # Simulating time delay (change to `86400` for real-time 24 hours)

    # Send reminders for unanswered emails
    send_reminder(gmail_service, unanswered_emails, reminder_hours=0.0014)  # Set to a few seconds for testing
