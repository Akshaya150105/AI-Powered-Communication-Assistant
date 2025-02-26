import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
import nltk
import pandas as pd
nltk.download('punkt', quiet=True)
from nltk.tokenize import sent_tokenize
from transformers import pipeline
from bs4 import BeautifulSoup
import time


st.set_page_config(
    page_title="Smart Gmail Summarizer",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #4285F4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #5f6368;
        margin-bottom: 2rem;
    }
    .card {
        background-color: #f9f9f9;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .email-sender {
        color: #34A853;
        font-weight: 500;
    }
    .email-date {
        color: #5f6368;
        font-size: 0.9rem;
    }
    .summary-box {
        background-color: #E8F0FE;
        border-left: 4px solid #4285F4;
        padding: 15px;
        border-radius: 4px;
    }
    .original-content {
        border: 1px solid #dadce0;
        border-radius: 8px;
        padding: 10px;
        margin-top: 10px;
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def authenticate_gmail():
    """Authenticate and return the Gmail API service."""
    try:
        with st.spinner("Authenticating with Gmail..."):
            flow = InstalledAppFlow.from_client_secrets_file("P:\\aks\\pages\\gmail\\credentials.json", SCOPES)
            creds = flow.run_local_server(port=57183)  
            
            
            service = build("gmail", "v1", credentials=creds)
            return service
    except Exception as e:
        st.error(f"Authentication error: {str(e)}")
        

def get_email_body(payload):
    """Extracts the email body, handling both plain text and HTML."""
    
    if "parts" in payload:
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")

            if mime_type == "text/plain" and "data" in part["body"]:  
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")

            elif mime_type == "text/html" and "data" in part["body"]:  
                html_content = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                return clean_text(html_content)

            elif "parts" in part:  
                return get_email_body(part)

    elif "body" in payload and "data" in payload["body"]:
        data = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        if payload.get("mimeType") == "text/html":
            return clean_text(data)
        return data

    return "[No Text Content]"

def clean_text(text):
    """Removes HTML tags and excessive whitespace."""
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ").strip()

def split_text(text, max_chunk_size=1024, overlap=100):
    """Splits text into sentence-based chunks for better summarization."""
    sentences = sent_tokenize(text)
    chunks, current_chunk = [], ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_chunk_size:
            current_chunk += " " + sentence
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence  # Start a new chunk

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

# Load summarization model on first run
@st.cache_resource
def load_summarizer():
    return pipeline("summarization", model="t5-base")

def dynamic_summarization(text, summarizer):
    """Summarizes long text dynamically based on size, avoiding over-summarization."""
    if not text or text == "[No Text Content]":
        return "[No content to summarize]"
    
    num_words = len(text.split())

    # Avoid summarizing very short emails
    if num_words < 50:
        return text  

    # Adjust summary size dynamically
    max_len = 80 if num_words < 300 else (130 if num_words < 600 else 200)

    # Split large text into chunks for better summarization
    chunks = split_text(text)

    if len(chunks) > 1:
        summaries = [summarizer(chunk, max_length=max_len, min_length=30, do_sample=False)[0]['summary_text'] for chunk in chunks]
        return " ".join(summaries)
    else:
        summary = summarizer(text, max_length=max_len, min_length=30, do_sample=False)
        return summary[0]["summary_text"]

def fetch_emails(service, user_id="me", max_results=5):
    """Fetches latest email messages and returns as structured data."""
    emails = []
    
    with st.spinner(f"Fetching your latest {max_results} emails..."):
        try:
            results = service.users().messages().list(userId=user_id, maxResults=max_results).execute()
            messages = results.get("messages", [])

            if not messages:
                st.info("No messages found in your inbox.")
                return []

            progress_bar = st.progress(0)
            summarizer = load_summarizer()
            
            for i, msg in enumerate(messages):
                message = service.users().messages().get(userId=user_id, id=msg["id"]).execute()
                payload = message["payload"]
                headers = payload["headers"]

                # Extract subject
                subject = next((header["value"] for header in headers if header["name"].lower() == "subject"), "No Subject")
                
                # Extract sender
                sender = next((header["value"] for header in headers if header["name"].lower() == "from"), "Unknown Sender")
                
                # Extract date
                date = next((header["value"] for header in headers if header["name"].lower() == "date"), "Unknown Date")
                
                # Extract and decode email body
                body = get_email_body(payload)
                
                # Summarize email body
                if body.strip() and body != "[No Text Content]":
                    summary = dynamic_summarization(body, summarizer)
                else:
                    summary = "[No text content to summarize]"
                
                emails.append({
                    "id": msg["id"],
                    "subject": subject,
                    "sender": sender,
                    "date": date,
                    "body": body,
                    "summary": summary
                })
                
                # Update progress
                progress_bar.progress((i + 1) / len(messages))
                
            progress_bar.empty()
            return emails
            
        except Exception as e:
            st.error(f"Error fetching emails: {str(e)}")
            return []

# Main app layout
def main():
    # Header section
    st.markdown('<div class="main-header">📧 Smart Gmail Summarizer</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Get quick summaries of your emails using AI</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.image("https://www.gstatic.com/images/branding/product/2x/gmail_2020q4_48dp.png", width=80)
        st.title("Controls")
        
        if "gmail_service" not in st.session_state:
            st.write("### Step 1: Connect to Gmail")
            if st.button("🔑 Authenticate with Gmail", use_container_width=True):
                service = authenticate_gmail()
                if service:
                    st.session_state["gmail_service"] = service
                    st.success("✅ Connected successfully!")
                    time.sleep(1)
                    st.rerun()
        else:
            st.write("### Connected to Gmail ✓")
            st.write("### Email Settings")
            
            # Email count selection
            num_emails = st.slider("Number of emails to fetch", min_value=1, max_value=20, value=5)
            
            if st.button("🔄 Fetch Emails", use_container_width=True):
                emails = fetch_emails(st.session_state["gmail_service"], max_results=num_emails)
                if emails:
                    st.session_state["emails"] = emails
                    st.success(f"✅ Fetched {len(emails)} emails!")
                    time.sleep(1)
                    st.rerun()
            
            if st.button("🚪 Log Out", use_container_width=True):
                st.session_state.pop("gmail_service", None)
                st.session_state.pop("emails", None)
                st.info("Logged out successfully")
                time.sleep(1)
                st.rerun()
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        This app uses AI to automatically summarize your Gmail messages, 
        saving you time and helping you focus on what matters.
        
        **Privacy Note**: Your email data never leaves your computer and 
        is processed locally.
        """)
    
    # Main content area
    if "gmail_service" in st.session_state:
        if "emails" in st.session_state:
            emails = st.session_state["emails"]
            
            # Display emails in tabs: Summary View and Table View
            tab1, tab2 = st.tabs(["📋 Summary View", "📊 Table View"])
            
            with tab1:
                if emails:
                    st.write(f"Showing {len(emails)} emails")
                    for i, email in enumerate(emails):
                        with st.expander(f"{email['subject']}"):
                            col1, col2 = st.columns([1, 4])
                            with col1:
                                st.markdown("**From:**")
                                st.markdown("**Date:**")
                                st.markdown("**Subject:**")
                            with col2:
                                st.markdown(f"<span class='email-sender'>{email['sender']}</span>", unsafe_allow_html=True)
                                st.markdown(f"<span class='email-date'>{email['date']}</span>", unsafe_allow_html=True)
                                st.markdown(f"{email['subject']}")
                            
                            st.markdown("---")
                            st.markdown("### Summary")
                            st.markdown(f"<div class='summary-box'>{email['summary']}</div>", unsafe_allow_html=True)
                            
                            # Show original content toggle
                            if st.checkbox(f"Show Original Content", key=f"show_original_{i}"):
                                st.markdown("### Original Content")
                                st.text_area("", email["body"], height=200, key=f"original_content_{i}")
                else:
                    st.info("No emails found in your inbox.")
            
            with tab2:
                if emails:
                    # Prepare data for table view
                    table_data = []
                    for email in emails:
                        table_data.append({
                            "Sender": email["sender"].split("<")[0].strip(),
                            "Subject": email["subject"],
                            "Date": email["date"],
                            "Summary": email["summary"][:100] + "..." if len(email["summary"]) > 100 else email["summary"]
                        })
                    
                    # Display as table
                    st.dataframe(pd.DataFrame(table_data), use_container_width=True)
                    
                    # Add detail view below table
                    st.markdown("### Email Details")
                    selected_email = st.selectbox(
                        "Select an email to view details",
                        options=range(len(emails)),
                        format_func=lambda i: emails[i]["subject"]
                    )
                    
                    if selected_email is not None:
                        email = emails[selected_email]
                        st.markdown(f"**From:** {email['sender']}")
                        st.markdown(f"**Date:** {email['date']}")
                        st.markdown(f"**Subject:** {email['subject']}")
                        
                        tab_summary, tab_original = st.tabs(["Summary", "Original Content"])
                        with tab_summary:
                            st.markdown(f"<div class='summary-box'>{email['summary']}</div>", unsafe_allow_html=True)
                        with tab_original:
                            st.text_area("", email["body"], height=300)
                else:
                    st.info("No emails found in your inbox.")
        else:
            # Placeholder when authenticated but no emails fetched yet
            st.info("👈 Use the sidebar to fetch your emails")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("""
                ### 🔍 Summarize
                Get AI-powered summaries of your emails to quickly understand their content
                """)
            with col2:
                st.markdown("""
                ### 🔎 Organize
                View your emails in a clean, organized interface
                """)
            with col3:
                st.markdown("""
                ### ⏱️ Save Time
                Process your inbox faster with automatic content analysis
                """)
    else:
        # Welcome screen when not authenticated
        st.markdown("## Welcome to Smart Gmail Summarizer!")
        st.markdown("### Get started in 3 easy steps:")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            ### 1️⃣ Connect
            Link your Gmail account securely using the sidebar
            """)
        with col2:
            st.markdown("""
            ### 2️⃣ Fetch
            Select how many emails to analyze
            """)
        with col3:
            st.markdown("""
            ### 3️⃣ Read
            Browse AI-generated summaries of your messages
            """)
            
        st.markdown("---")
        st.info("👈 Click 'Authenticate with Gmail' in the sidebar to get started")

if __name__ == "__main__":
    main()