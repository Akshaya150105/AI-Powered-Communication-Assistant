import streamlit as st
import pickle
import base64
import numpy as np
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.errors import HttpError
from sentence_transformers import SentenceTransformer
from joblib import load
import pandas as pd

# Set page configuration
st.set_page_config(
    page_title="Smart Email Classifier",
    page_icon="📧",
    layout="wide"
)

# Constants
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
MODEL_PATH = "P:\\aks\\pages\\gmail\email_classifier.pkl"
CREDENTIALS_PATH = "P:\\aks\\pages\\gmail\\credentials.json"
TOKEN_PATH = "token.pickle"
CATEGORY_MAPPING = {0: "Low Priority", 1: "Urgent", 2: "Follow Up"}
CATEGORY_COLORS = {
    "Low Priority": "green",
    "Urgent": "red",
    "Follow Up": "orange"
}


st.title("📧 Smart Email Classifier")
st.markdown("""
This app connects to your Gmail account, fetches recent emails, and classifies them 
by priority using a machine learning model. 
""")


@st.cache_resource
def load_model():
    """Load the sentence transformer model"""
    return SentenceTransformer("all-MiniLM-L6-v2")

@st.cache_resource
def load_classifier():
    """Load the trained classifier"""
    try:
        with open(MODEL_PATH, "rb") as f:
            return load(f)
    except FileNotFoundError:
        st.error(f"Model file '{MODEL_PATH}' not found. Please ensure it exists in the current directory.")
        return None

def authenticate_gmail():
    """Authenticate and return the Gmail API service."""
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as token:
            creds = pickle.load(token)
    else:
        try:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=8080)
            # Save the credentials for the next run
            with open(TOKEN_PATH, "wb") as token:
                pickle.dump(creds, token)
        except FileNotFoundError:
            st.error(f"Credentials file '{CREDENTIALS_PATH}' not found.")
            return None
        
    try:
        service = build("gmail", "v1", credentials=creds)
        return service
    except HttpError as error:
        st.error(f"An error occurred: {error}")
        return None

def get_email_body(payload):
    """Extracts email body (handles both plain text and HTML)."""
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and "data" in part["body"]:
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
    elif "body" in payload and "data" in payload["body"]:
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
    return "[No Text Content]"

def classify_email(email_text, model, classifier):
    """Encodes email text and predicts its category."""
    email_embedding = model.encode([email_text], convert_to_tensor=False)
    
    
    email_embedding = np.array(email_embedding).reshape(1, -1)
    
    predicted_category = classifier.predict(email_embedding)[0]
    return CATEGORY_MAPPING.get(predicted_category, "Unknown")

def get_messages(service, model, classifier, max_results=10):
    """Fetches and classifies emails."""
    try:
        results = service.users().messages().list(userId="me", maxResults=max_results).execute()
        messages = results.get("messages", [])
        
        if not messages:
            st.info("No emails found.")
            return []
        
        email_data = []
        with st.spinner("Fetching and analyzing emails..."):
            for msg in messages:
                message = service.users().messages().get(userId="me", id=msg["id"]).execute()
                payload = message["payload"]
                headers = payload["headers"]
                
                subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
                sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "Unknown Sender")
                
                body = get_email_body(payload)
                category = classify_email(body, model, classifier)
                
                email_data.append({
                    "id": msg["id"],
                    "subject": subject,
                    "sender": sender,
                    "body": body,
                    "category": category
                })
        
        return email_data
    except HttpError as error:
        st.error(f"An error occurred: {error}")
        return []

# Main app logic
def main():
    # Load model and classifier
    model = load_model()
    classifier = load_classifier()
    
    if classifier is None:
        st.warning("Please upload or create the email classifier model before proceeding.")
        return
    
    # Sidebar controls
    with st.sidebar:
        st.header("Controls")
        
        if st.button("🔑 Authenticate Gmail"):
            st.session_state.gmail_service = authenticate_gmail()
            if st.session_state.gmail_service:
                st.success("Authentication successful!")
            
        max_emails = st.slider("Number of emails to fetch", min_value=5, max_value=50, value=10)
        
        st.divider()
        st.subheader("Filter Options")
        category_filter = st.multiselect(
            "Filter by category",
            options=list(CATEGORY_MAPPING.values()),
            default=list(CATEGORY_MAPPING.values())
        )
    
    # Initialize session state
    if 'gmail_service' not in st.session_state:
        st.session_state.gmail_service = None
    
    if 'emails' not in st.session_state:
        st.session_state.emails = []
    
    # Main content
    if st.session_state.gmail_service:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if st.button("🔄 Fetch Emails"):
                st.session_state.emails = get_messages(
                    st.session_state.gmail_service, 
                    model, 
                    classifier, 
                    max_results=max_emails
                )
        
        with col2:
            st.write(f"Total emails fetched: {len(st.session_state.emails)}")
        
    
        if st.session_state.emails:
            # Filter emails based on category selection
            filtered_emails = [email for email in st.session_state.emails if email["category"] in category_filter]
            
            # Create dataframe for clean display
            df = pd.DataFrame(filtered_emails)
            
            # Summary by category
            st.subheader("📊 Email Summary by Category")
            category_counts = df['category'].value_counts().reset_index()
            category_counts.columns = ['Category', 'Count']
            
            col1, col2, col3 = st.columns(3)
            for i, row in category_counts.iterrows():
                category = row['Category']
                count = row['Count']
                color = CATEGORY_COLORS.get(category, "gray")
                
                if i % 3 == 0:
                    with col1:
                        st.metric(label=category, value=count)
                elif i % 3 == 1:
                    with col2:
                        st.metric(label=category, value=count)
                else:
                    with col3:
                        st.metric(label=category, value=count)
            
            # Display individual emails
            st.subheader("📥 Classified Emails")
            for i, email in enumerate(filtered_emails):
                with st.expander(f"{email['subject']} - {email['category']}"):
                    st.markdown(f"**From:** {email['sender']}")
                    st.markdown(f"**Category:** <span style='color:{CATEGORY_COLORS.get(email['category'], 'gray')}'>{email['category']}</span>", unsafe_allow_html=True)
                    st.text_area("Email Body", email['body'], height=200, key=f"email_{i}")
    else:
        st.info("Please authenticate with Gmail using the button in the sidebar to get started.")

    # Footer
    st.divider()
    st.caption("Email Classifier - Powered by Machine Learning")

if __name__ == "__main__":
    main()