import streamlit as st
import base64
import email
import time
import json
import os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd

# App Configuration
st.set_page_config(
    page_title="Email Reminder Assistant",
    page_icon="📧",
    layout="wide"
)

# Constants
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
CREDENTIALS_PATH = "P:\\aks\\pages\\gmail\\credentials.json"
TOKEN_PATH = "token.json"
SAVED_EMAILS_PATH = "unanswered_emails.json"

# App title and description
st.title("📧 Email Reminder Assistant")
st.markdown("""
This app helps you stay on top of important unanswered emails by tracking them and sending reminder notifications.
""")

# Helper functions
def authenticate_gmail():
    """Authenticate and return the Gmail API service."""
    try:
        creds = None
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_info(
                json.loads(open(TOKEN_PATH).read()), SCOPES)
        
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=8080)
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
                
        service = build("gmail", "v1", credentials=creds)
        return service
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return None

def get_email_body(payload):
    """Extract and decode the email body from payload."""
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain" and "data" in part["body"]:
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
    elif "body" in payload and "data" in payload["body"]:
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
    return "No body available."

def list_important_unanswered_messages(service, user_id="me", max_results=10):
    """Fetches important unanswered emails and flags them for follow-up."""
    try:
        # Customize query based on user preferences
        query = "is:unread is:important -from:me -in:chats"
        results = service.users().messages().list(userId=user_id, maxResults=max_results, q=query).execute()
        messages = results.get("messages", [])
        
        if not messages:
            return []

        email_data = []
        with st.spinner("Fetching important unanswered emails..."):
            for msg in messages:
                message = service.users().messages().get(userId=user_id, id=msg["id"]).execute()
                payload = message["payload"]
                headers = payload["headers"]
                
                subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
                sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")
                date_str = next((h["value"] for h in headers if h["name"] == "Date"), None)
                
                # Parse the date
                try:
                    # This is a simplification - email dates can be complex
                    email_date = datetime.strptime(date_str.split(' +')[0], '%a, %d %b %Y %H:%M:%S')
                except:
                    email_date = datetime.utcnow()
                
                body = get_email_body(payload)
                
                email_data.append({
                    "id": msg["id"],
                    "subject": subject,
                    "sender": sender,
                    "received_date": email_date.isoformat(),
                    "tracked_since": datetime.utcnow().isoformat(),
                    "body": body[:500] + ("..." if len(body) > 500 else ""),
                    "reminder_sent": False,
                    "last_reminder": None
                })
        
        return email_data
    except Exception as e:
        st.error(f"Error fetching messages: {e}")
        return []

def add_label(service, message_id, label_name):
    """Adds a label to an email."""
    try:
        # Get all labels
        labels = service.users().labels().list(userId="me").execute().get("labels", [])
        label_id = next((l["id"] for l in labels if l["name"] == label_name), None)
        
        # Create label if it doesn't exist
        if not label_id:
            label_obj = {
                "name": label_name, 
                "labelListVisibility": "labelShow", 
                "messageListVisibility": "show"
            }
            created_label = service.users().labels().create(userId="me", body=label_obj).execute()
            label_id = created_label["id"]
        
        # Add label to message
        service.users().messages().modify(
            userId="me", 
            id=message_id, 
            body={"addLabelIds": [label_id]}
        ).execute()
        
        return True
    except Exception as e:
        st.error(f"Failed to add label: {e}")
        return False

def send_email(service, to_email, subject, body):
    """Sends an email using Gmail API."""
    try:
        message = MIMEText(body)
        message["To"] = to_email
        message["Subject"] = subject
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        sent_message = service.users().messages().send(
            userId="me", 
            body={"raw": encoded_message}
        ).execute()
        
        return sent_message
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return None

def save_emails_to_file(emails):
    """Save tracked emails to a JSON file."""
    try:
        with open(SAVED_EMAILS_PATH, 'w') as f:
            json.dump(emails, f)
    except Exception as e:
        st.error(f"Error saving emails: {e}")

def load_emails_from_file():
    """Load tracked emails from JSON file."""
    if not os.path.exists(SAVED_EMAILS_PATH):
        return []
    try:
        with open(SAVED_EMAILS_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading emails: {e}")
        return []

def send_reminder_for_email(service, email_data, reminder_email, custom_message=None):
    """Send a reminder for a specific email."""
    subject = f"Reminder: {email_data['subject']}"
    
    if custom_message:
        body = custom_message
    else:
        body = f"""
Hi,

This is a reminder about an unanswered important email:

From: {email_data['sender']}
Subject: {email_data['subject']}
Received: {email_data['received_date']}

Email Preview:
{email_data['body'][:200]}...

Please check your inbox and respond to this email.

Best regards,
Your Email Assistant
"""
    
    result = send_email(service, reminder_email, subject, body)
    if result:
        return datetime.utcnow().isoformat()
    return None

# Initialize session state for tracked emails
if 'tracked_emails' not in st.session_state:
    st.session_state.tracked_emails = load_emails_from_file()

if 'gmail_service' not in st.session_state:
    st.session_state.gmail_service = None

# Sidebar configuration
with st.sidebar:
    st.header("Settings")
    
    if st.button("🔑 Authenticate Gmail"):
        service = authenticate_gmail()
        if service:
            st.session_state.gmail_service = service
            st.success("Authentication successful!")
    
    st.divider()
    
    reminder_email = st.text_input(
        "Your reminder email address",
        placeholder="example@gmail.com",
        value="22pd05@gmail.com" if "reminder_email" not in st.session_state else st.session_state.reminder_email
    )
    st.session_state.reminder_email = reminder_email
    
    max_emails = st.slider("Number of emails to fetch", 5, 50, 10)
    
    st.divider()
    
    if st.button("📋 Clear All Tracked Emails"):
        st.session_state.tracked_emails = []
        save_emails_to_file([])
        st.success("All tracked emails cleared!")

# Main app layout
tabs = st.tabs(["Track Emails", "Manage Reminders", "Settings"])

with tabs[0]:
    st.header("Track Important Unanswered Emails")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if st.button("🔍 Fetch New Emails", use_container_width=True):
            if st.session_state.gmail_service:
                new_emails = list_important_unanswered_messages(
                    st.session_state.gmail_service,
                    max_results=max_emails
                )
                
                if new_emails:
                    # Label emails in Gmail
                    for email in new_emails:
                        add_label(st.session_state.gmail_service, email["id"], "Pending Reply")
                    
                    # Add to tracked emails (avoid duplicates)
                    tracked_ids = [e["id"] for e in st.session_state.tracked_emails]
                    new_emails = [e for e in new_emails if e["id"] not in tracked_ids]
                    st.session_state.tracked_emails.extend(new_emails)
                    save_emails_to_file(st.session_state.tracked_emails)
                    
                    st.success(f"Found {len(new_emails)} new important unanswered emails!")
                else:
                    st.info("No new important unanswered emails found.")
            else:
                st.warning("Please authenticate with Gmail first.")
    
    # Display currently tracked emails
    if st.session_state.tracked_emails:
        st.subheader(f"Currently Tracking {len(st.session_state.tracked_emails)} Emails")
        
        # Convert to DataFrame for display
        df = pd.DataFrame([
            {
                "Subject": e["subject"],
                "Sender": e["sender"],
                "Received": e["received_date"][:10],
                "Reminder Sent": "Yes" if e["reminder_sent"] else "No",
                "ID": e["id"]
            } for e in st.session_state.tracked_emails
        ])
        
        st.dataframe(df, use_container_width=True)
        
        # Email detail view
        st.subheader("Email Details")
        email_id = st.selectbox("Select an email to view details", 
                                 options=[e["id"] for e in st.session_state.tracked_emails],
                                 format_func=lambda x: next((e["subject"] for e in st.session_state.tracked_emails if e["id"] == x), x))
        
        selected_email = next((e for e in st.session_state.tracked_emails if e["id"] == email_id), None)
        if selected_email:
            st.markdown(f"**From:** {selected_email['sender']}")
            st.markdown(f"**Subject:** {selected_email['subject']}")
            st.markdown(f"**Received:** {selected_email['received_date']}")
            st.markdown(f"**Reminder Status:** {'Sent on ' + selected_email['last_reminder'] if selected_email['reminder_sent'] else 'Not sent'}")
            st.text_area("Email Body", selected_email['body'], height=200)
            
            # Individual email actions
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📤 Send Reminder Now", key=f"remind_{email_id}", use_container_width=True):
                    if st.session_state.gmail_service and reminder_email:
                        reminder_time = send_reminder_for_email(st.session_state.gmail_service, selected_email, reminder_email)
                        if reminder_time:
                            for i, email in enumerate(st.session_state.tracked_emails):
                                if email["id"] == email_id:
                                    st.session_state.tracked_emails[i]["reminder_sent"] = True
                                    st.session_state.tracked_emails[i]["last_reminder"] = reminder_time
                            save_emails_to_file(st.session_state.tracked_emails)
                            st.success("Reminder sent successfully!")
                    else:
                        st.warning("Please authenticate and provide a reminder email.")
            
            with col2:
                if st.button("❌ Remove from Tracking", key=f"remove_{email_id}", use_container_width=True):
                    st.session_state.tracked_emails = [e for e in st.session_state.tracked_emails if e["id"] != email_id]
                    save_emails_to_file(st.session_state.tracked_emails)
                    st.success("Email removed from tracking.")
                    st.rerun()
    else:
        st.info("No emails are currently being tracked. Click 'Fetch New Emails' to start.")

with tabs[1]:
    st.header("Email Reminder Management")
    
    # Configure automatic reminders
    st.subheader("Reminder Settings")
    
    col1, col2 = st.columns(2)
    with col1:
        reminder_hours = st.number_input("Send reminders after (hours)", 
                                         min_value=1, 
                                         max_value=72, 
                                         value=24,
                                         help="Automatically send reminders this many hours after tracking an email")
    
    with col2:
        custom_message = st.text_area("Custom reminder message (optional)", 
                                      placeholder="Leave blank for default message",
                                      height=100)
    
    if st.button("🔄 Check and Send Due Reminders"):
        if st.session_state.gmail_service and reminder_email:
            now = datetime.utcnow()
            reminders_sent = 0
            
            for i, email in enumerate(st.session_state.tracked_emails):
                if not email["reminder_sent"]:
                    tracked_since = datetime.fromisoformat(email["tracked_since"])
                    if now - tracked_since >= timedelta(hours=reminder_hours):
                        reminder_time = send_reminder_for_email(
                            st.session_state.gmail_service, 
                            email, 
                            reminder_email,
                            custom_message if custom_message else None
                        )
                        
                        if reminder_time:
                            st.session_state.tracked_emails[i]["reminder_sent"] = True
                            st.session_state.tracked_emails[i]["last_reminder"] = reminder_time
                            reminders_sent += 1
            
            if reminders_sent > 0:
                save_emails_to_file(st.session_state.tracked_emails)
                st.success(f"Sent {reminders_sent} reminders!")
            else:
                st.info("No reminders due at this time.")
        else:
            st.warning("Please authenticate and provide a reminder email.")
    
    # Display reminder history
    st.subheader("Reminder History")
    
    reminder_history = [e for e in st.session_state.tracked_emails if e["reminder_sent"]]
    if reminder_history:
        history_df = pd.DataFrame([
            {
                "Subject": e["subject"],
                "Sender": e["sender"], 
                "Reminder Sent": e["last_reminder"][:16].replace("T", " at ")
            } for e in reminder_history
        ])
        st.dataframe(history_df, use_container_width=True)
    else:
        st.info("No reminders have been sent yet.")

with tabs[2]:
    st.header("Application Settings")
    
    st.subheader("Email Query Settings")
    query_help = """
    Customize how the app searches for important emails:
    - `is:unread` - Only unread emails
    - `is:important` - Only important emails
    - `-from:me` - Exclude emails sent by you
    - `-in:chats` - Exclude chat messages
    - `from:example@gmail.com` - Only from specific sender
    
    You can combine these in different ways.
    """
    
    custom_query = st.text_input(
        "Custom email search query",
        value="is:unread is:important -from:me -in:chats",
        help=query_help
    )
    
    st.subheader("Label Settings")
    custom_label = st.text_input(
        "Custom Gmail label for tracked emails",
        value="Pending Reply",
        help="This label will be added to all tracked emails in Gmail"
    )
    
    if st.button("💾 Save Settings"):
        st.session_state.custom_query = custom_query
        st.session_state.custom_label = custom_label
        st.success("Settings saved!")

# Footer
st.divider()
st.caption("Email Reminder Assistant - Stay on top of your important communications")