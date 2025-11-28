from jamaibase import JamAI, protocol
import os
from dotenv import load_dotenv

load_dotenv()

# New Credentials provided by user
JAMAI_API_KEY = os.getenv("BOOKING_API_KEY")
JAMAI_PROJECT_ID = os.getenv("BOOKING_PROJECT_ID")

jamai = JamAI(token=JAMAI_API_KEY, project_id=JAMAI_PROJECT_ID)

print(f"Listing tables for project: {JAMAI_PROJECT_ID}...")

try:
    # List tables (Action Tables and Knowledge Tables)
    # Note: The SDK method might vary, trying common ones.
    # Usually list_tables returns a list of table objects.
    
    # Try fetching action tables (chat tables are usually action tables or just 'tables')
    tables = jamai.table.list_tables(table_type="chat") 
    
    print(f"Found {len(tables.items)} chat tables:")
    for table in tables.items:
        print(f" - ID: {table.id}")

except Exception as e:
    print(f"Error listing tables: {e}")
