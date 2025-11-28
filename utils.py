import streamlit as st
import requests
from jamaibase import JamAI, protocol
from auth import supabase_staff
import os
import tempfile
import json, uuid
import re
from datetime import datetime, timedelta

# --- Configuration & Mock JAM AI Integration ---

# WARNING: In a production environment, NEVER expose API keys directly in client-side code.
# Use environment variables (st.secrets) and a secure backend for actual API calls.
from dotenv import load_dotenv
load_dotenv()

# Default/Fallback Credentials (kept for backward compatibility with imports)
# NOTE: These are intentionally set to None to enforce explicit bot selection.
# If you see an error here, it means code is trying to use a default bot instead of a specific one.
JAMAI_API_KEY = None 
JAMAI_PROJECT_ID = None
JAMAI_TABLE_ID = None
JAMAI_KNOWLEDGE_TABLE_ID = None
# require these all none for each of api key is to ensure robustness and for security purpose
# and for connection i did force selecting for each api frontend call ,hence each html file consisting corresponding context that match to their function
 
# --- MULTI-BOT CONFIGURATION ---
# We map contexts to specific credentials.
BOT_CONFIG = {
    "Staff": {
        "api_key": os.getenv("STAFF_API_KEY"),
        "project_id": os.getenv("STAFF_PROJECT_ID"),
        "table_id": os.getenv("STAFF_TABLE_ID"),
        # Staff bot only uses Action Table, no Knowledge Table
        "knowledge_table_id": None 
    },
    "Public": {
        "api_key": os.getenv("PUBLIC_API_KEY"),
        "project_id": os.getenv("PUBLIC_PROJECT_ID"),
        "table_id": os.getenv("PUBLIC_TABLE_ID"),
        "knowledge_table_id": os.getenv("PUBLIC_KNOWLEDGE_TABLE_ID")
    },
    "Booking": {
        "api_key": os.getenv("BOOKING_API_KEY"),
        "project_id": os.getenv("BOOKING_PROJECT_ID"),
        "table_id": os.getenv("BOOKING_TABLE_ID"),
        "knowledge_table_id": os.getenv("BOOKING_KNOWLEDGE_TABLE_ID")
    }
}

# Initialize default JamAI client (can be overridden in functions)
# We initialize this lazily or with dummy values if needed, but ideally we shouldn't use this global instance anymore.
# jamai_client = JamAI(token=JAMAI_API_KEY, project_id=JAMAI_PROJECT_ID) 
jamai_client = None # Force error if used globally

def get_duty_list_context():
    """Fetches and formats the duty list from Supabase."""
    if not supabase_staff:
        return ""
    try:
        response = supabase_staff.table('DutyList').select("*").execute()
        if not response.data:
            return ""
        
        context = "\n\n--- CURRENT CLINIC DUTY LIST ---\n"
        for row in response.data:
            # Format each row as a readable string
            # e.g. {'doctor_name': 'Dr. Smith', 'day': 'Monday'} -> "doctor_name: Dr. Smith, day: Monday"
            row_str = ", ".join([f"{k}: {v}" for k, v in row.items()])
            context += f"- {row_str}\n"
        context += "--------------------------------\n"
        return context
    except Exception as e:
        print(f"Error fetching duty list: {e}")
        return ""

def get_booking_list_context(role="Public", user_email=None):
    """Fetches and formats the booking list from Supabase."""
    if not supabase_staff:
        return ""
    try:
        # Fetch bookings
        # For Staff: Fetch all upcoming bookings
        # For Public: Fetch only their bookings if email is provided
        
        query = supabase_staff.table('Booking').select("*")
        
        # Filter for upcoming bookings (today onwards)
        today = datetime.now().strftime('%Y-%m-%d')
        query = query.gte('Date', today)
        
        if role == "Public" and user_email:
            # Filter by patient email/name
            # Note: The column is 'patient_name' but we store email there in book_endpoint
            query = query.eq('patient_name', user_email)
        elif role == "Public" and not user_email:
            # If public and no email, return nothing to avoid leaking info
            return ""
            
        response = query.execute()
        
        if not response.data:
            return ""
        
        context = "\n\n--- UPCOMING BOOKINGS ---\n"
        for row in response.data:
            # Format: Date: YYYY-MM-DD, Time: HH:MM, Doctor: Name, Patient: Name (if staff)
            row_str = f"Date: {row.get('Date')}, Time: {row.get('appoinment_time')}, Doctor: {row.get('doctor_name')}"
            if role == "Staff":
                row_str += f", Patient: {row.get('patient_name')}"
            context += f"- {row_str}\n"
        context += "-------------------------\n"
        return context
    except Exception as e:
        print(f"Error fetching booking list: {e}")
        return ""

def create_booking(doctor_name, date, time, patient_email):
    """Creates a new booking in the Supabase database."""
    if not supabase_staff:
        return {'success': False, 'message': 'Database connection not available.'}
    
    try:
        # Basic validation
        if not doctor_name or not date or not time:
            return {'success': False, 'message': 'Missing required booking details.'}

        booking_data = {
            "doctor_name": doctor_name,
            "patient_name": patient_email or "Guest",
            "appoinment_time": time,
            "Date": date
        }
        response = supabase_staff.table('Booking').insert(booking_data).execute()
        return {'success': True, 'data': response.data}
    except Exception as e:
        print(f"Create Booking Error: {e}")
        return {'success': False, 'message': str(e)}

def cancel_booking(doctor_name, date, time, patient_email):
    """Cancels a booking in the Supabase database."""
    if not supabase_staff:
        return {'success': False, 'message': 'Database connection not available.'}
    
    try:
        # Basic validation
        if not doctor_name or not date or not time:
            return {'success': False, 'message': 'Missing required booking details to identify the appointment.'}

        # Delete the booking matching the criteria
        # Note: We use patient_email to ensure users can only cancel their own bookings (if provided)
        query = supabase_staff.table('Booking').delete().eq('doctor_name', doctor_name).eq('Date', date).eq('appoinment_time', time)
        
        if patient_email:
            query = query.eq('patient_name', patient_email)
            
        response = query.execute()
        
        # Check if any row was actually deleted
        if response.data and len(response.data) > 0:
            return {'success': True, 'data': response.data}
        else:
            return {'success': False, 'message': 'No matching booking found to cancel.'}
            
    except Exception as e:
        print(f"Cancel Booking Error: {e}")
        return {'success': False, 'message': str(e)}

def create_new_chat_table(table_id_src):
    new_table_id = f"chat_{str(uuid.uuid4())[:8]}"
    config = BOT_CONFIG["Public"]
    client = JamAI(token=config["api_key"], project_id=config["project_id"])

    try:
        client.table.duplicate_table(
            table_type="chat",
            table_id_src=table_id_src,  # Your base agent ID
            table_id_dst=new_table_id,
            include_data=True,
            create_as_child=True
        )
        return new_table_id
    except Exception as e:
        print(f"Error creating new chat: {str(e)}")
        return None

def delete_table(table_type, table_id):
    config = BOT_CONFIG["Public"]
    client = JamAI(token=config["api_key"], project_id=config["project_id"])
    try:
        client.table.delete_table(
            table_type=table_type,
            table_id=table_id,
        )
        return True
    except Exception as e:
        print(f"Error deleting chat: {str(e)}")
        return False

def post_chat_table(user_message, table_id):
    config = BOT_CONFIG["Public"]
    client = JamAI(token=config["api_key"], project_id=config["project_id"])

    try:
        # Debugging: Print data being sent
        print(f"DEBUG chat: Sending row data to JamAI: {user_message}")

        completion = client.table.add_table_rows(
            table_type="chat",
            request=protocol.MultiRowAddRequest(
                table_id=table_id,
                data=[{"User": user_message}],
                stream=False
            )
        )

        if completion.rows and len(completion.rows) > 0:
            row_columns = completion.rows[0].columns

            print(f"DEBUG: Received columns from JamAI: {list(row_columns.keys())}")

            if "user_output" in row_columns:
                return f"User: {user_message}\n Action Table: {row_columns['user_output'].text}"
            else:
                return list(row_columns.values())[-1].text
        else:
            return "Error: No response received from JamAI Table."

    except Exception as e:
        return f"Error connecting to JamAI: {str(e)}"

def get_public_jam_ai_response(user_message, session_id=None, user_email=None):
    """
    Dedicated function for Public context interactions with JamAI.
    """
    try:
        config = BOT_CONFIG["Public"]
        
        # Initialize a specific client for this request
        client = JamAI(token=config["api_key"], project_id=config["project_id"])
        # target_table_id = config["table_id"] # Not used, we use "staff FAQ"

        # Retrieve session_id from Streamlit state if available and not provided
        if session_id is None:
            try:
                session_id = st.session_state.get('session_id', 'unknown_session')
            except:
                session_id = 'external_session'
        
        user_role = "Public"
        
        # Fetch Duty List Context
        duty_context = get_duty_list_context()
        
        # Fetch Booking List Context
        booking_context = get_booking_list_context(user_role, user_email)
        
        # Combine User Message with Context
        full_message = user_message
        if duty_context:
            full_message += duty_context
        if booking_context:
            full_message += booking_context

        # Debugging: Print data being sent
        # print(f"DEBUG: Sending row data to JamAI (Public): {row_data}")

        completion = client.table.add_table_rows(
            table_type="action",
            request=protocol.MultiRowAddRequest(
                table_id="FAQ",
                data=[{"usr_input": full_message}], 
                stream=False 
            )
        )
        
        if completion.rows and len(completion.rows) > 0:
            # Get the first row's columns
            row_columns = completion.rows[0].columns
            
            # Debugging: Print received columns to console
            print(f"DEBUG: Received columns from JamAI: {list(row_columns.keys())}")
            
            # Find the 'user_output' column or the last column which usually contains the response
            if "user_output" in row_columns:
                ai_response = row_columns["user_output"].text
            else:
                # Fallback: return the text of the last column
                ai_response = list(row_columns.values())[-1].text
            
            return f"User: {user_message}\n Action Table: {ai_response}"

        else:
            return "Error: No response received from JamAI Table."

    except Exception as e:
        return f"Error connecting to JamAI: {str(e)}"

def get_public_chat_history(table_id):
    """
    Fetches chat history for a specific session from the JamAI Table.
    """
    config = BOT_CONFIG["Public"]
    client = JamAI(token=config["api_key"], project_id=config["project_id"])
    
    try:
        print(f"DEBUG: Fetching history for table_id: '{table_id}'")
        
        all_items = []
        offset = 0
        limit = 100
        max_pages = 30 
        
        for _ in range(max_pages):
            response = client.table.list_table_rows(
                table_type="chat", 
                table_id=table_id,
                limit=limit,
                offset=offset
            )
            
            if not response.items:
                break
                
            all_items.extend(response.items)
            
            if len(response.items) < limit:
                break
                
            offset += limit
        
        history = []
        if all_items:
            print(f"DEBUG: Found {len(all_items)} total rows in table.")
            
            for row in all_items:
                if isinstance(row, dict):
                    columns = row
                    def get_text(col_name):
                        if col_name in columns:
                            col_data = columns[col_name]
                            if isinstance(col_data, dict) and 'value' in col_data:
                                return col_data['value']
                            return str(col_data)
                        return ""
                    def extract_user_message(text): 
                        match = re.search(r'User:\s*(.*?)\s*Action Table:', text, re.DOTALL)
                        if match:
                            return match.group(1).strip()
                        return text
                    def get_timestamp():
                        if 'Updated at' in row:
                            return str(row['Updated at'])
                        if 'Created at' in row:
                            return str(row['Created at'])
                        return "Unknown Time"
                else:
                    columns = row.columns
                    def get_text(col_name):
                        if col_name in columns:
                            return columns[col_name].text
                        return ""
                    def extract_user_message(text): 
                        match = re.search(r'User:\s*(.*?)\s*Action Table:', text, re.DOTALL)
                        if match:
                            return match.group(1).strip()
                        return text
                    def get_timestamp():
                        if hasattr(row, 'updated_at') and row.updated_at:
                            return str(row.updated_at)
                        if hasattr(row, 'created_at') and row.created_at:
                            return str(row.created_at)
                        return "Unknown Time"

                raw_text = get_text("User")
                user_text = extract_user_message(raw_text) 
                ai_text = get_text("AI")
                timestamp = get_timestamp()

                if user_text:
                    history.append({
                        "role": "user",
                        "content": user_text,
                        "timestamp": timestamp
                    })
                if ai_text:
                    history.append({
                        "role": "assistant",
                        "content": ai_text,
                        "timestamp": timestamp
                    })
            
            history.sort(key=lambda x: x['timestamp'])
            print(f"DEBUG: Found {len(history)} messages for this session.")
            
        return history

    except Exception as e:
        print(f"Error fetching history: {e}")
        return [{
            "role": "assistant",
            "content": f"⚠️ **Connection Error**: Could not load chat history. {str(e)}",
            "timestamp": "System"
        }]

def get_staff_jam_ai_response(user_message, session_id=None, user_email=None):
    """
    Dedicated function for Staff context interactions with JamAI.
    Uses Action Table only.
    """
    try:
        config = BOT_CONFIG["Staff"]
        
        # Initialize a specific client for this request
        client = JamAI(token=config["api_key"], project_id=config["project_id"])
        target_table_id = config["table_id"]

        # Retrieve session_id from Streamlit state if available and not provided
        if session_id is None:
            try:
                session_id = st.session_state.get('session_id', 'unknown_session')
            except:
                session_id = 'external_session'
        
        user_role = "Staff"
        
        # Fetch Duty List Context
        duty_context = get_duty_list_context()
        
        # Fetch Booking List Context
        booking_context = get_booking_list_context(user_role, user_email)
        
        # Combine User Message with Context
        full_message = user_message
        if duty_context:
            full_message += duty_context
        if booking_context:
            full_message += booking_context

        # Prepare row data with metadata for logging
        row_data = {
            "User": full_message,
            "Session ID": session_id,
            "User Role": user_role
        }

        # Add User Email if provided
        if user_email:
            row_data["User Email"] = user_email
        
        # Debugging: Print data being sent
        print(f"DEBUG: Sending row data to JamAI (Staff): {row_data}")

        completion = client.table.add_table_rows(
            table_type="action",
            request=protocol.MultiRowAddRequest(
                table_id=target_table_id,
                data=[row_data], 
                stream=False 
            )
        )
        
        if completion.rows and len(completion.rows) > 0:
            # Get the first row's columns
            row_columns = completion.rows[0].columns
            
            # Debugging: Print received columns to console
            print(f"DEBUG: Received columns from JamAI: {list(row_columns.keys())}")
            
            # Find the 'AI' column or the last column which usually contains the response
            if "AI" in row_columns:
                ai_response = row_columns["AI"].text
            else:
                # Fallback: return the text of the last column
                ai_response = list(row_columns.values())[-1].text
            
            return ai_response

        else:
            return "Error: No response received from JamAI Table."

    except Exception as e:
        return f"Error connecting to JamAI: {str(e)}"

def get_booking_jam_ai_response(user_message, session_id=None, user_email=None):
    """
    Dedicated function for Booking context interactions with JamAI.
    Uses Chat Table only.
    """
    try:
        config = BOT_CONFIG["Booking"]
        
        # Initialize a specific client for this request
        client = JamAI(token=config["api_key"], project_id=config["project_id"])
        target_table_id = config["table_id"]

        # Retrieve session_id from Streamlit state if available and not provided
        if session_id is None:
            try:
                session_id = st.session_state.get('session_id', 'unknown_session')
            except:
                session_id = 'external_session'
        
        user_role = "Public"
        
        # Fetch Duty List Context
        duty_context = get_duty_list_context()
        
        # Fetch Booking List Context
        booking_context = get_booking_list_context(user_role, user_email)
        
        # Combine User Message with Context
        full_message = user_message
        if duty_context:
            full_message += duty_context
        if booking_context:
            full_message += booking_context

        # Debugging: Print data being sent
        print(f"DEBUG: Sending row data to JamAI (Booking): {full_message}")

        completion = client.table.add_table_rows(
            table_type="chat",
            request=protocol.MultiRowAddRequest(
                table_id=target_table_id,
                data=[{"User": full_message}],
                stream=False 
            )
        )
        
        if completion.rows and len(completion.rows) > 0:
            # Get the first row's columns
            row_columns = completion.rows[0].columns
            
            # Debugging: Print received columns to console
            print(f"DEBUG: Received columns from JamAI: {list(row_columns.keys())}")
            
            # Find the 'AI' column or the last column which usually contains the response
            if "AI" in row_columns:
                ai_response = row_columns["AI"].text
            else:
                # Fallback: return the text of the last column
                ai_response = list(row_columns.values())[-1].text
            
            return ai_response

        else:
            return "Error: No response received from JamAI Table."

    except Exception as e:
        return f"Error connecting to JamAI: {str(e)}"

def get_jam_ai_response(project_id, user_message, model_context, session_id=None, user_email=None):
    """
    Function to call the JAM AI API using the Table interface.
    This ensures we use the specific project/table configuration (models, prompts) you built in JamAI.
    """
    
    try:
        # --- DYNAMIC BOT SELECTION ---
        # Determine which bot config to use based on context
        bot_type = "Public" # Default
        if "staff" in model_context.lower():
            bot_type = "Staff"
        elif "booking" in model_context.lower():
            bot_type = "Booking"
        
        # Dispatch to dedicated functions
        if bot_type == "Public":
            return get_public_jam_ai_response(user_message, session_id, user_email)
        elif bot_type == "Staff":
            return get_staff_jam_ai_response(user_message, session_id, user_email)
        elif bot_type == "Booking":
            return get_booking_jam_ai_response(user_message, session_id, user_email)
            
        return "Error: Unknown bot context."

    except Exception as e:
        return f"Error connecting to JamAI: {str(e)}"

def check_staff_login():
    """Checks if the user is logged in as staff and redirects if not."""
    if 'is_staff' not in st.session_state or not st.session_state['is_staff']:
        st.warning("Please log in as a staff member on the main page to access this portal.")
        # Streamlit multi-page structure handles the "redirection" by just showing the warning 
        # and stopping the rest of the page from executing.
        st.stop()

def get_chat_history(session_id):
    """
    Fetches chat history for a specific session from the JamAI Table.
    """
    try:
        print(f"DEBUG: Fetching history for session_id: '{session_id}'")
        
        # Determine which bot to use based on session_id prefix
        # session_id format: 'staff_...', 'patient_...', 'booking_...'
        bot_type = "Public"
        table_type = "action" # Default to action table

        if str(session_id).startswith("staff_"):
            bot_type = "Staff"
            table_type = "action"
        elif str(session_id).startswith("booking_"):
            bot_type = "Booking"
            table_type = "chat" # Booking bot uses Chat Table
            
        config = BOT_CONFIG.get(bot_type, BOT_CONFIG["Public"])
        
        # Initialize client specifically for this history fetch
        client = JamAI(token=config["api_key"], project_id=config["project_id"])
        target_table_id = config["table_id"]
        
        all_items = []
        offset = 0
        limit = 100
        max_pages = 30 # Fetch up to 3000 rows
        
        for _ in range(max_pages):
            response = client.table.list_table_rows(
                table_type=table_type,
                table_id=target_table_id,
                limit=limit,
                offset=offset
            )
            
            if not response.items:
                break
                
            all_items.extend(response.items)
            
            if len(response.items) < limit:
                break
                
            offset += limit
        
        history = []
        if all_items:
            print(f"DEBUG: Found {len(all_items)} total rows in table.")
            
            for row in all_items:
                # Handle row being a dict (newer SDK) or object (older SDK)
                if isinstance(row, dict):
                    columns = row
                    # Helper to get text value from column dict
                    def get_text(col_name):
                        if col_name in columns:
                            col_data = columns[col_name]
                            if isinstance(col_data, dict) and 'value' in col_data:
                                return col_data['value']
                            return str(col_data)
                        return ""
                    
                    # Safe timestamp extraction for dict
                    def get_timestamp():
                        if 'Updated at' in row:
                            return str(row['Updated at'])
                        if 'Created at' in row:
                            return str(row['Created at'])
                        return "Unknown Time"

                else:
                    columns = row.columns
                    def get_text(col_name):
                        if col_name in columns:
                            return columns[col_name].text
                        return ""
                    
                    # Safe timestamp extraction for object
                    def get_timestamp():
                        if hasattr(row, 'updated_at') and row.updated_at:
                            return str(row.updated_at)
                        if hasattr(row, 'created_at') and row.created_at:
                            return str(row.created_at)
                        return "Unknown Time"

                # Check if 'Session ID' column exists
                # For dicts, we check keys. For objects, we check .columns keys
                has_session_id = "Session ID" in columns if isinstance(columns, dict) else "Session ID" in columns
                
                if has_session_id:
                    row_session_id = get_text("Session ID")
                    
                    # Strict string comparison with stripping
                    if row_session_id and str(row_session_id).strip() == str(session_id).strip():
                        user_text = get_text("User")
                        ai_text = get_text("AI")
                        timestamp = get_timestamp()
                        
                        # Add User Message
                        if user_text:
                            history.append({
                                "role": "user",
                                "content": user_text,
                                "timestamp": timestamp
                            })
                        # Add AI Message
                        if ai_text:
                            history.append({
                                "role": "assistant",
                                "content": ai_text,
                                "timestamp": timestamp
                            })
            
            # Sort by timestamp to ensure correct order (oldest first)
            history.sort(key=lambda x: x['timestamp'])
            print(f"DEBUG: Found {len(history)} messages for this session.")
            
        return history

    except Exception as e:
        print(f"Error fetching history: {e}")
        # Return a system error message so the user knows something went wrong
        return [{
            "role": "assistant",
            "content": f"⚠️ **Connection Error**: Could not load chat history. The server returned: *{str(e)}*. Please check your API key or internet connection.",
            "timestamp": "System"
        }]

def embed_file_in_jamai(file_path, bot_type="Public"):
    """
    Embeds a file into a JamAI table.
    """
    try:
        config = BOT_CONFIG.get(bot_type)
        if not config:
            raise ValueError(f"Invalid bot_type: {bot_type}")
            
        table_id = config.get("knowledge_table_id")
        if not table_id:
             # Fallback or error if no knowledge table is configured for this bot
             # For Staff, maybe we don't support uploads, or maybe we default to Public?
             # For now, let's raise an error to be safe.
             raise ValueError(f"No knowledge table configured for bot_type: {bot_type}")

        # Initialize client for this specific bot
        client = JamAI(token=config["api_key"], project_id=config["project_id"])

        response = client.table.embed_file(
            file_path=file_path,
            table_id=table_id,
        )
        return response
    except Exception as e:
        print(f"Error embedding file: {e}")
        raise e