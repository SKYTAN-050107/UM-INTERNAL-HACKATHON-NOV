from jamaibase import JamAI
import os
# this page is for public access
# Credentials from utils.py
JAMAI_API_KEY = "jamai_pat_749e7aefdeedf3d72d92af598864a4d6fbfded21b53b4264"
JAMAI_PROJECT_ID = "proj_e3a75abd600c7b03e7542674"

client = JamAI(token=JAMAI_API_KEY, project_id=JAMAI_PROJECT_ID)

try:
    # Try to list chat tables
    print("Fetching Action Tables...")
    tables = client.table.list_tables(table_type="action")
    for t in tables.items:
        print(f"Found Action Table: {t.id}")

    print("\nFetching Chat Tables...")
    tables = client.table.list_tables(table_type="chat")
    for t in tables.items:
        print(f"Found Chat Table: {t.id}")
        
    print("\nFetching Knowledge Tables...")
    tables = client.table.list_tables(table_type="knowledge")
    for t in tables.items:
        print(f"Found Knowledge Table: {t.id}")

except Exception as e:
    print(f"Error: {e}")
