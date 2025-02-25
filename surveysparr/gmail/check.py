import os

file_path = "email_classifier.pkl"
print("File exists:", os.path.exists(file_path))
print("File size:", os.path.getsize(file_path), "bytes")