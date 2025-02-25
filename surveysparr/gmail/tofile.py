import sqlite3
import pandas as pd

# Database and output file path
DB_PATH = "emails.db"  # Replace with your database file
CSV_FILE = "emails_exported.csv"  # Output CSV file

# Connect to the database
conn = sqlite3.connect(DB_PATH)

# Load the table into a Pandas DataFrame
query = "SELECT * FROM emails"  # Replace 'emails' with your table name
df = pd.read_sql_query(query, conn)

# Close the connection
conn.close()

# Save DataFrame to CSV
df.to_csv(CSV_FILE, index=False, encoding="utf-8")
print(f"✅ Table exported to '{CSV_FILE}' successfully.")
