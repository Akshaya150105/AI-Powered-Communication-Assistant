import pickle
import base64
import numpy as np
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from sentence_transformers import SentenceTransformer
from joblib import load

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def authenticate_gmail():
    """Authenticate and return the Gmail API service."""
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=8080)
    service = build("gmail", "v1", credentials=creds)
    return service

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
    
    # Ensure the embedding is in 2D format: (1, num_features)
    email_embedding = np.array(email_embedding).reshape(1, -1)

    predicted_category = classifier.predict(email_embedding)[0]
    CATEGORY_MAPPING = {0: "Low Priority", 1: "Urgent", 2: "Follow Up"}
    return CATEGORY_MAPPING.get(predicted_category, "Unknown")

def get_messages(service, model, classifier, max_results=5):
    """Fetches and classifies emails."""
    results = service.users().messages().list(userId="me", maxResults=max_results).execute()
    messages = results.get("messages", [])

    if not messages:
        print("No emails found.")
        return

    for msg in messages:
        message = service.users().messages().get(userId="me", id=msg["id"]).execute()
        payload = message["payload"]
        headers = payload["headers"]

        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")

        body = get_email_body(payload)
        category = classify_email(body, model, classifier)

        print(f"\n📩 Subject: {subject}")
        print(f"📨 From: {sender}")
        print(f"📜 Email Body (Preview): {body[:200]}...")
        print(f"🔹 Predicted Category: {category}")
        print("-" * 50)

if __name__ == "__main__":
    # Load trained model
    with open("email_classifier.pkl", "rb") as f:
        classifier = load(f)  # Corrected the file loading

    # Load SentenceTransformer model (change the model if necessary)
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Authenticate Gmail API
    gmail_service = authenticate_gmail()

    # Fetch and classify emails
    get_messages(gmail_service, model, classifier, max_results=5)
