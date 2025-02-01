# AI-Powered SQL Chat Assistant

## 📌 Overview
This AI-powered chatbot allows users to interact with an SQLite database using natural language queries. The chatbot converts user queries into SQL statements, fetches data from the database, and returns the results in a human-readable format.

## 🚀 How It Works
1. **User Input:** The user enters a natural language query (e.g., *"Who is the manager of the Sales department?"*).
2. **AI Processing:** The chatbot uses `Llama-2-13B-chat-GGML` to convert the input into a valid SQL query.
3. **Query Validation:** The assistant checks if the entities (departments, employees, etc.) exist in the database before execution.
4. **Database Execution:** The SQL query runs on an SQLite database.
5. **Response:** The assistant returns the requested information or an appropriate error message if the entity is not found or the query is invalid.

## 🛠️ Running the Project Locally
### Prerequisites
- Python 3.8+
- SQLite3
- Flask & Required Python Packages
- `TheBloke/Llama-2-13B-chat-GGML` model files

### Installation & Setup
1. **Clone the repository**
   ```sh
   git clone https://github.com/your-repo/sql-chat-assistant.git
   cd sql-chat-assistant
   ```
2. **Install dependencies**
   ```sh
   pip install -r requirements.txt
   ```
3. **Ensure the SQLite database (`database.db`) is set up**
   ```sh
   sqlite3 database.db < schema.sql
   ```
4. **Run the Flask server**
   ```sh
   python app.py
   ```
5. **Access the assistant**
   - The API runs at: `http://127.0.0.1:5001/query`
   - Send a POST request with JSON:  
     ```json
     {"query": "Who is the manager of the Sales department?"}
     ```

## 🌐 Deploying on Render
1. Push the project to GitHub.
2. Create a **New Web Service** on [Render](https://render.com/).
3. Connect the GitHub repository.
4. Set up build & start commands:
   ```sh
   pip install -r requirements.txt
   python app.py
   ```
5. Deploy and get a public URL to test your chatbot.

## ⚠️ Known Limitations & Future Improvements
- **Limited Query Support**: Currently supports basic SQL queries related to employees and departments.
- **Database Dependency**: Responses depend on existing database records.
- **Query Optimization**: AI-generated SQL queries may require refinement for complex use cases.
- **Enhancements**:
  - Expand query types for broader functionality.
  - Improve NLP handling to avoid incorrect SQL generation.
  - Add authentication to restrict database access.

## 📬 Feedback & Contributions
Feel free to submit issues or contribute improvements via pull requests!

