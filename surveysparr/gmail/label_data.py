import sqlite3
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer, util

# Database Path
DB_PATH = "emails.db"

# Load emails from SQLite database
def load_emails_from_db():
    """Fetch email data from SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT id, sender, receiver, subject, email_body FROM emails"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Load emails
df = load_emails_from_db()

# Ensure subject and email_body are not NaN
df["subject"] = df["subject"].fillna("")
df["email_body"] = df["email_body"].fillna("")
df["combined_text"] = df["subject"] + " " + df["email_body"]

# Define keyword-based rule for urgent and follow-up emails
def check_keywords(text):
    urgent_keywords = [
        "urgent", "asap", "immediately", "important", "attention",
        "deadline", "last chance", "final reminder", "expires soon",
        "closes tonight", "last day", "emergency", "help", "please respond",
        "action required", "immediate response needed", "help needed",
        "critical", "time-sensitive", "high priority", "response needed",
        "act now", "don't miss out", "security alert", "account issue",
        "billing issue", "fraud alert", "server down", "payment failure",
        "important update", "final notice", "urgent request", "risk alert"
    ]
    followup_keywords = [
        "follow up", "reminder", "check in", "status", "progress",
        "event date", "registration required", "mandatory", "competition", "exam",
        "meeting update", "pending response", "next steps", "waiting for reply",
        "action pending", "documents required", "confirmation needed", 
        "reschedule request", "training session", "policy update", 
        "contract renewal", "submission deadline", "schedule update"
    ]
    
    text_lower = text.lower()
    
    if any(word in text_lower for word in urgent_keywords):
        return "Urgent"
    elif any(word in text_lower for word in followup_keywords):
        return "Follow Up"
    return None

# Load Sentence-BERT model (optimized for GPU if available)
device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer("all-MiniLM-L6-v2", device=device)

# Define categories with sample phrases
categories = {
    "Urgent": "This email requires immediate attention. It is critical and has a deadline. It may involve emergency or action required.",
    "Follow Up": "This email needs a follow-up or status update. It is a reminder about something important.",
    "Low Priority": "This is an informational or promotional email that does not require urgent action."
}

# Encode category descriptions into embeddings
category_embeddings = {label: model.encode(text, convert_to_tensor=True) for label, text in categories.items()}

# Encode email combined text into embeddings
email_embeddings = model.encode(df["combined_text"].tolist(), convert_to_tensor=True)

# Similarity threshold for classification
SIMILARITY_THRESHOLD = 0.55

# Assign category using hybrid method
def classify_email(email_text, email_embedding):
    keyword_label = check_keywords(email_text)
    
    if keyword_label:
        return keyword_label  # Directly assign if urgent or follow-up keywords are detected

    scores = {label: util.pytorch_cos_sim(email_embedding, embedding).item() for label, embedding in category_embeddings.items()}
    
    max_label, max_score = max(scores.items(), key=lambda item: item[1])
    
    if max_score >= SIMILARITY_THRESHOLD:
        return max_label
    else:
        return "Low Priority"

# Classify emails
df["category"] = [classify_email(email, embedding) for email, embedding in zip(df["combined_text"], email_embeddings)]

# Save labeled emails back to the database
def save_labeled_emails(df):
    """Save labeled emails back to SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Add category column if it doesn't exist
    cursor.execute("PRAGMA table_info(emails)")
    columns = [row[1] for row in cursor.fetchall()]
    if "category" not in columns:
        cursor.execute("ALTER TABLE emails ADD COLUMN category TEXT")
        conn.commit()

    # Update each row with the assigned category
    for _, row in df.iterrows():
        cursor.execute("UPDATE emails SET category = ? WHERE id = ?", (row["category"], row["id"]))

    conn.commit()
    conn.close()
    print("✅ Emails updated with categories in SQLite database.")

# Save categorized emails
save_labeled_emails(df)

print("✅ Emails labeled and saved successfully.")
