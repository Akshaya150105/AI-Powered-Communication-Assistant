import sqlite3
import pandas as pd
import joblib
import torch
from sentence_transformers import SentenceTransformer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from imblearn.over_sampling import SMOTE


DB_PATH = "emails.db"

def load_emails_from_db():
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT id, email_body, category FROM emails"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    df["email_body"] = df["email_body"].fillna("").astype(str)
    return df

df = load_emails_from_db()

category_mapping = {"Low Priority": 0, "Urgent": 1, "Follow Up": 2}
df["category"] = df["category"].map(category_mapping)

# Check class distribution before applying SMOTE
print("Class distribution before SMOTE:")
print(df["category"].value_counts())

# Load Sentence-BERT model
device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer("all-MiniLM-L6-v2", device=device)

# Convert email texts to embeddings
email_embeddings = model.encode(df["email_body"].tolist(), convert_to_tensor=False)

# Split dataset into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(email_embeddings, df["category"], test_size=0.2, random_state=42, stratify=df["category"])

# Apply SMOTE
smote = SMOTE(random_state=42)
X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)

# Check class distribution after SMOTE
print("Class distribution after SMOTE:")
print(pd.Series(y_train_resampled).value_counts())

# Train the classifier
clf = RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced")
clf.fit(X_train_resampled, y_train_resampled)

# Predict and evaluate model performance
y_pred = clf.predict(X_test)
print("\n🎯 Model Performance:")
print("✅ Accuracy:", accuracy_score(y_test, y_pred))
print("✅ Classification Report:\n", classification_report(y_test, y_pred))

# Save the trained model and category mapping
joblib.dump(clf, "email_classifier.pkl")
joblib.dump(category_mapping, "category_mapping.pkl")
print("\n✅ Model training complete and saved as 'email_classifier_rf.pkl'")

# Hybrid classification function
def classify_email(text):
    urgent_keywords = ["urgent", "asap", "immediately", "important", "attention", "deadline", "final reminder", "security alert"]
    followup_keywords = ["follow up", "reminder", "status", "next steps", "pending response"]
    
    text_lower = text.lower()
    if any(word in text_lower for word in urgent_keywords):
        return "Urgent"
    elif any(word in text_lower for word in followup_keywords):
        return "Follow Up"
    
    # If no keyword match, use ML model
    embedding = model.encode([text], convert_to_tensor=False)
    pred_label = clf.predict(embedding)[0]
    return {v: k for k, v in category_mapping.items()}[pred_label]

# Test on a sample email
for email in ["Please respond immediately", "Please respond immediately, we need this document urgently.","Can you follow up on this request?"]:
    predicted_category = classify_email(email)
    print(f" '{email}' → {predicted_category}")
