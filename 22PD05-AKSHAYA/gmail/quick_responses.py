import os
import base64
import re
import time
import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch


SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

@st.cache_resource
def load_model():
    """Load the DialoGPT model."""
    tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-medium")
    tokenizer.padding_side = 'left'
    model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-medium")
    return tokenizer, model

def get_gmail_service():
    """Authenticate and create Gmail API service."""
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'P:\\aks\\pages\\gmail\\credentials.json', SCOPES)
            creds = flow.run_local_server(port=57183)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)

def clean_email_text(email_body):
    """Clean and truncate email text."""
    # Remove quoted replies (lines starting with >)
    cleaned = re.sub(r'^>.*$', '', email_body, flags=re.MULTILINE)
    
    # Remove common signature indicators
    cleaned = re.sub(r'--\s*\n.*', '', cleaned, flags=re.DOTALL)
    
    # Remove "On [date], [person] wrote:" patterns
    cleaned = re.sub(r'On\s+.*wrote:.*', '', cleaned, flags=re.DOTALL)
    
    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned

def classify_email_intent(email_body):
    """Determine the intent of the email to select appropriate template."""
    email_lower = email_body.lower()
    
    # Define patterns for common inquiries
    patterns = {
        "pricing": r'(price|cost|quote|pricing|rates|how much)',
        "services": r'(services|offer|provide|work|technologies)',
        "meeting": r'(meet|meeting|schedule|appointment|available|availability)',
        "timeline": r'(timeline|deadline|when|status|update|progress)',
        "support": r'(help|issue|problem|trouble|not working)',
        "general": r'.*'  # Fallback
    }
    
    # Check for matches
    for intent, pattern in patterns.items():
        if re.search(pattern, email_lower):
            return intent
    
    return "general"

def generate_templated_response(intent, sender_email):
    """Generate a response based on email intent using templates."""
    # Get sender name from email
    sender_name = sender_email.split('@')[0] if '@' in sender_email else 'there'
    
    # Templates for different types of inquiries
    templates = {
        "pricing": f"""Hello {sender_name},

Thank you for your interest in our services. Our pricing structure depends on the specific requirements of your project. 

For web development, our rates typically range from $75-150 per hour depending on complexity. We also offer fixed-price packages for standard websites.

Would you be available for a quick call to discuss your specific needs?

Best regards,
Your Name
Company
Phone: (555) 123-4567""",

        "services": f"""Hello {sender_name},

Thank you for your interest in our services. We specialize in:

- Full-stack web development
- Mobile application development
- E-commerce solutions
- UI/UX design
- CMS implementation

I'd be happy to discuss how we can help with your specific project.

Best regards,
Your Name
Company
Phone: (555) 123-4567""",

        "meeting": f"""Hello {sender_name},

Thank you for reaching out about scheduling a meeting. I'd be happy to discuss a potential collaboration.

Please let me know a few dates and times that work for you, and I'll confirm my availability.

Looking forward to our conversation.

Best regards,
Your Name
Company
Phone: (555) 123-4567""",

        "timeline": f"""Hello {sender_name},

Thank you for checking in on the project. We're making good progress according to our timeline.

I'll send you a detailed update by the end of the day with our current status and next steps.

Best regards,
Your Name
Company
Phone: (555) 123-4567""",

        "support": f"""Hello {sender_name},

I'm sorry to hear you're experiencing issues. We'll help resolve this as quickly as possible.

Could you please provide more details about the problem you're facing? This will help us address it more effectively.

Best regards,
Your Name
Support Team
Company""",

        "general": f"""Hello {sender_name},

Thank you for your message. I've received your email and will respond in detail shortly.

Best regards,
Your Name
Company
Phone: (555) 123-4567"""
    }
    
    return templates.get(intent, templates["general"])

def generate_response(email_body, sender_email, tokenizer, model):
    """Generate a response to an email."""
    try:
        # Clean the email body
        cleaned_body = clean_email_text(email_body)
        
        # Get the first 500 characters for intent classification
        short_content = cleaned_body[:500]
        
        # Classify the email intent
        intent = classify_email_intent(short_content)
        
        # For most intents, use a template response
        if intent != "general":
            return intent, generate_templated_response(intent, sender_email)
        
        # For general emails, try DialoGPT but with truncated input
        truncated_body = short_content[:200]
        
        # Check token count to avoid errors
        tokens = tokenizer.encode(truncated_body)
        if len(tokens) > 512:
            return intent, generate_templated_response("general", sender_email)
        
    
        inputs = tokenizer.encode(truncated_body + tokenizer.eos_token, return_tensors="pt")
        
        # Generate a response with reasonable length limits
        reply_ids = model.generate(
            inputs,
            max_length=100,
            pad_token_id=tokenizer.eos_token_id,
            no_repeat_ngram_size=3,
            do_sample=True,
            top_k=50,
            top_p=0.95,
            temperature=0.7
        )
        
        response = tokenizer.decode(reply_ids[:, inputs.shape[-1]:][0], skip_special_tokens=True)
        
        # Add a signature
        response += "\n\nBest regards,\nYour Name\nCompany\nPhone: (555) 123-4567"
        
        return intent, response
    
    except Exception as e:
        st.error(f"Error generating response: {e}")
        return "general", generate_templated_response("general", sender_email)

def create_message(to, subject, message_text, thread_id=None):
    """Create a message for an email."""
    message = MIMEText(message_text)
    message['to'] = to
    message['subject'] = subject
    
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    body = {'raw': raw_message}
    if thread_id:
        body['threadId'] = thread_id
    
    return body

def fetch_unread_emails(service):
    """Fetch unread emails from Gmail."""
    try:
        results = service.users().messages().list(
            userId='me', 
            q='is:unread -label:automated_reply',
            maxResults=10 
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return []
            
        email_list = []
        
        for message in messages:
            try:
                # Get the message details
                msg = service.users().messages().get(userId='me', id=message['id']).execute()
                
                # Get the sender and subject
                headers = msg['payload']['headers']
                sender = next((header['value'] for header in headers if header['name'] == 'From'), None)
                subject = next((header['value'] for header in headers if header['name'] == 'Subject'), '(No Subject)')
                date = next((header['value'] for header in headers if header['name'] == 'Date'), None)
                
                # Extract email address from sender format
                sender_email = re.search(r'<(.+?)>', sender) if sender else None
                sender_email = sender_email.group(1) if sender_email else sender
                
                # Get the thread ID
                thread_id = msg['threadId']
                
                # Get the email body
                email_body = ""
                
                if 'parts' in msg['payload']:
                    parts = msg['payload']['parts']
                    for part in parts:
                        if part['mimeType'] == 'text/plain':
                            if 'data' in part['body']:
                                email_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                            break
                elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
                    email_body = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode('utf-8')
                
                if not email_body:
                    email_body = "(No content)"
                
                email_list.append({
                    'id': message['id'],
                    'thread_id': thread_id,
                    'sender': sender,
                    'sender_email': sender_email,
                    'subject': subject,
                    'date': date,
                    'body': email_body,
                    'snippet': msg.get('snippet', '(No preview available)')
                })
                
            except Exception as e:
                st.error(f"Error processing message {message['id']}: {e}")
                continue
                
        return email_list
        
    except Exception as e:
        st.error(f"Error fetching emails: {e}")
        return []

def send_email_reply(service, email_data, response_text):
    """Send a reply to the selected email."""
    try:
        reply = create_message(
            to=email_data['sender'],
            subject=f"Re: {email_data['subject']}" if not email_data['subject'].startswith('Re:') else email_data['subject'],
            message_text=response_text,
            thread_id=email_data['thread_id']
        )
        
        service.users().messages().send(userId='me', body=reply).execute()
        
        
        service.users().messages().modify(
            userId='me', 
            id=email_data['id'],
            body={'addLabelIds': ['AUTOMATED_REPLY'], 'removeLabelIds': ['UNREAD']}
        ).execute()
        
        return True
    except Exception as e:
        st.error(f"Error sending reply: {e}")
        return False

def initialize_labels(service):
    
    try:
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        label_exists = any(label['name'] == 'AUTOMATED_REPLY' for label in labels)
        
        if not label_exists:
            label = {
                'name': 'AUTOMATED_REPLY',
                'messageListVisibility': 'show',
                'labelListVisibility': 'labelShow'
            }
            service.users().labels().create(userId='me', body=label).execute()
            st.success("Created 'AUTOMATED_REPLY' label")
    except Exception as e:
        st.error(f"Error creating label: {e}")

def main():
    st.set_page_config(page_title="Email Assistant", page_icon="✉️", layout="wide")
    
    st.title("✉️ Email Assistant")
    st.write("Review and send automated responses to your emails")
    
    # Initialize session state for storing email data
    if 'emails' not in st.session_state:
        st.session_state.emails = []
    if 'current_email_index' not in st.session_state:
        st.session_state.current_email_index = 0
    if 'generated_response' not in st.session_state:
        st.session_state.generated_response = ""
    if 'response_intent' not in st.session_state:
        st.session_state.response_intent = ""
    if 'service' not in st.session_state:
        st.session_state.service = None
    if 'model_loaded' not in st.session_state:
        st.session_state.model_loaded = False
    
    # Load model
    if not st.session_state.model_loaded:
        with st.spinner("Loading AI model..."):
            tokenizer, model = load_model()
            st.session_state.tokenizer = tokenizer
            st.session_state.model = model
            st.session_state.model_loaded = True
    
    # Authenticate with Gmail API
    if st.session_state.service is None:
        try:
            with st.spinner("Authenticating with Gmail..."):
                service = get_gmail_service()
                initialize_labels(service)
                st.session_state.service = service
                st.success("Successfully connected to Gmail!")
        except Exception as e:
            st.error(f"Authentication error: {e}")
            st.info("Please make sure credentials.json is in the current directory.")
            return
    
    # Create sidebar for actions
    with st.sidebar:
        st.subheader("Actions")
        if st.button("🔄 Refresh Inbox"):
            with st.spinner("Fetching emails..."):
                st.session_state.emails = fetch_unread_emails(st.session_state.service)
                st.session_state.current_email_index = 0
                if st.session_state.emails:
                    st.success(f"Found {len(st.session_state.emails)} unread emails")
                else:
                    st.info("No unread emails found")
        
        if st.session_state.emails:
            st.subheader("Email Navigation")
            st.write(f"Showing email {st.session_state.current_email_index + 1} of {len(st.session_state.emails)}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⬅️ Previous") and st.session_state.current_email_index > 0:
                    st.session_state.current_email_index -= 1
                    st.session_state.generated_response = ""
            with col2:
                if st.button("➡️ Next") and st.session_state.current_email_index < len(st.session_state.emails) - 1:
                    st.session_state.current_email_index += 1
                    st.session_state.generated_response = ""
    
    # Initial load of emails if none are loaded
    if not st.session_state.emails:
        st.info("Click 'Refresh Inbox' to fetch your unread emails")
    
    # Display current email and response options
    if st.session_state.emails and st.session_state.current_email_index < len(st.session_state.emails):
        current_email = st.session_state.emails[st.session_state.current_email_index]
        
        # Email details section
        st.subheader("Email Details")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**From:** {current_email['sender']}")
            st.markdown(f"**Subject:** {current_email['subject']}")
        with col2:
            st.markdown(f"**Date:** {current_email['date']}")
        
        # Email content
        st.subheader("Email Content")
        with st.expander("Show full email content", expanded=True):
            st.text_area("Body", current_email['body'], height=200, disabled=True)
        
        # Generate response button
        if not st.session_state.generated_response:
            if st.button("🤖 Generate Response"):
                with st.spinner("Generating response..."):
                    intent, response = generate_response(
                        current_email['body'], 
                        current_email['sender_email'],
                        st.session_state.tokenizer,
                        st.session_state.model
                    )
                    st.session_state.generated_response = response
                    st.session_state.response_intent = intent
        
        # Display and edit response
        if st.session_state.generated_response:
            st.subheader("Generated Response")
            st.info(f"Detected intent: {st.session_state.response_intent.upper()}")
            
            edited_response = st.text_area(
                "Edit response before sending", 
                st.session_state.generated_response,
                height=300
            )
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.button("✅ Send Reply"):
                    with st.spinner("Sending reply..."):
                        success = send_email_reply(
                            st.session_state.service,
                            current_email,
                            edited_response
                        )
                        if success:
                            st.success("Reply sent successfully!")
                            # Remove the email from the list and reset the response
                            st.session_state.emails.pop(st.session_state.current_email_index)
                            if st.session_state.emails:
                                if st.session_state.current_email_index >= len(st.session_state.emails):
                                    st.session_state.current_email_index = len(st.session_state.emails) - 1
                            else:
                                st.session_state.current_email_index = 0
                            st.session_state.generated_response = ""
                            st.experimental_rerun()
            
            with col2:
                if st.button("🔄 Regenerate"):
                    st.session_state.generated_response = ""
                    st.experimental_rerun()
            
            with col3:
                if st.button("⏭️ Skip Email"):
                    # Mark as read without sending a reply
                    try:
                        st.session_state.service.users().messages().modify(
                            userId='me', 
                            id=current_email['id'],
                            body={'removeLabelIds': ['UNREAD']}
                        ).execute()
                        st.info("Email marked as read (skipped)")
                        st.session_state.emails.pop(st.session_state.current_email_index)
                        if st.session_state.emails:
                            if st.session_state.current_email_index >= len(st.session_state.emails):
                                st.session_state.current_email_index = len(st.session_state.emails) - 1
                        else:
                            st.session_state.current_email_index = 0
                        st.session_state.generated_response = ""
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Error skipping email: {e}")
    
    # Show empty state if no emails after processing
    if st.session_state.emails and st.session_state.current_email_index >= len(st.session_state.emails):
        st.info("No more unread emails to process. Click 'Refresh Inbox' to check for new emails.")

if __name__ == '__main__':
    main()