# ClinicConnect

ClinicConnect is an AI-powered healthcare assistant platform designed to streamline clinic operations and enhance patient engagement. It features specialized chatbots for different user roles, leveraging **JamAI** for intelligent natural language processing and **Supabase** for real-time data management.

## Features

- **Multi-Role AI Assistants:**
  - **Public Bot:** Provides general information, answers patient queries, and assists with symptom checking.
  - **Staff Bot:** An internal tool for clinic staff to view duty lists, check schedules, and manage clinic operations.
  - **Booking Bot:** A dedicated assistant for scheduling and managing patient appointments.
- **Real-Time Data Integration:** Seamlessly connects with Supabase to fetch and update live data such as doctor duty lists and appointment schedules.
- **Context-Aware Interactions:** The AI agents are aware of the current clinic context, ensuring accurate and relevant responses.
- **Knowledge Base Management:** Supports uploading and embedding documents to expand the AI's knowledge base dynamically.
- **Role-Based Access Control:** Secure login system distinguishing between staff and public access.

## Installation

Follow these steps to set up the project locally.

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd UMHACKATHONINTERNAL-main
   ```

2. **Install dependencies**
   Ensure you have Python installed. Then run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**
   Create a `.env` file in the root directory and add the following keys:

   ```env
   # Supabase Configuration
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_anon_key

   # Staff Bot Configuration
   STAFF_API_KEY=your_jamai_api_key
   STAFF_PROJECT_ID=your_project_id
   STAFF_TABLE_ID=your_action_table_id

   # Public Bot Configuration
   PUBLIC_API_KEY=your_jamai_api_key
   PUBLIC_PROJECT_ID=your_project_id
   PUBLIC_TABLE_ID=your_action_table_id
   PUBLIC_KNOWLEDGE_TABLE_ID=your_knowledge_table_id

   # Booking Bot Configuration
   BOOKING_API_KEY=your_jamai_api_key
   BOOKING_PROJECT_ID=your_project_id
   BOOKING_TABLE_ID=your_chat_table_id
   BOOKING_KNOWLEDGE_TABLE_ID=your_knowledge_table_id
   ```

## Usage

1. **Start the Server**
   Run the Flask application:
   ```bash
   python server.py
   ```

2. **Access the Application**
   Open your web browser and navigate to:
   ```
   http://localhost:5001
   ```

3. **Navigate the Interface**
   - **Main Page:** Choose between Patient or Staff portals.
   - **Patient Portal:** Chat with the Public bot or make bookings.
   - **Staff Portal:** Log in to access the Staff Dashboard and internal chatbot.

## Project Structure

```
/
├── auth.py              # Authentication logic (Supabase)
├── server.py            # Main Flask application server
├── utils.py             # Core logic for JamAI integration and database operations
├── requirements.txt     # Python dependencies
├── site_config.json     # Site configuration settings
├── static/              # Frontend assets (HTML, CSS, JS)
│   ├── booking.html
│   ├── dashboard.html
│   ├── main_page.html
│   ├── patient_chat.html
│   ├── staff_chat.html
│   └── style.css
└── resources/           # Additional resources
```

## Configuration

The application relies on a `.env` file for sensitive credentials. Ensure all API keys and Project IDs are correctly set up in your JamAI and Supabase projects before running the application.

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/YourFeature`).
3. Commit your changes (`git commit -m "Add some feature"`).
4. Push to the branch (`git push origin feature/YourFeature`).
5. Open a Pull Request.

## License

Distributed under the MIT License.

## Acknowledgements

- **JamAI Base** for the LLM infrastructure.
- **Supabase** for the backend database.
- **Flask** for the web framework.
