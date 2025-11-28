from jamaibase import JamAI
import os
from dotenv import load_dotenv

load_dotenv()

JAMAI_API_KEY = os.getenv("PUBLIC_API_KEY")
JAMAI_PROJECT_ID = os.getenv("PUBLIC_PROJECT_ID")

client = JamAI(token=JAMAI_API_KEY, project_id=JAMAI_PROJECT_ID)

try:
    # Try to list tables. The method might be list_tables or similar on the table resource
    tables = client.table.list_tables(table_type="chat")
    print("Tables found:")
    for t in tables.items:
        print(f"- ID: {t.id}, Name: {t.id}") # Usually ID is the name or similar
except Exception as e:
    print(f"Error listing tables: {e}")
