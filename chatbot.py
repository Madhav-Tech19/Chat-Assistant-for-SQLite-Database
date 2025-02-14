import sqlite3
import re
from huggingface_hub import hf_hub_download
from llama_cpp import Llama
from flask import Flask, request, jsonify
from flask_cors import CORS
from ctransformers import AutoModelForCausalLM

# Connect to SQLite
conn = sqlite3.connect("company.db")
cursor = conn.cursor()

# Create Employees table
cursor.execute("""
CREATE TABLE IF NOT EXISTS Employees (
    ID INTEGER PRIMARY KEY,
    Name TEXT NOT NULL,
    Department TEXT NOT NULL,
    Salary INTEGER NOT NULL,
    Hire_Date TEXT NOT NULL
);
""")

# Create Departments table
cursor.execute("""
CREATE TABLE IF NOT EXISTS Departments (
    ID INTEGER PRIMARY KEY,
    Name TEXT NOT NULL,
    Manager TEXT NOT NULL
);
""")

try:
    cursor.executemany("""
    INSERT INTO Employees (ID, Name, Department, Salary, Hire_Date)
    VALUES (?, ?, ?, ?, ?);
    """, [
        (1, "Alice", "Sales", 50000, "2021-01-15"),
        (2, "Bob", "Engineering", 70000, "2020-06-10"),
        (3, "Charlie", "Marketing", 60000, "2022-03-20")
    ])

    cursor.executemany("""
    INSERT INTO Departments (ID, Name, Manager)
    VALUES (?, ?, ?);
    """, [
        (1, "Sales", "Alice"),
        (2, "Engineering", "Bob"),
        (3, "Marketing", "Charlie")
    ])
    # Commit changes
    conn.commit()
    print("Database setup complete!")
except sqlite3.OperationalError as e:
    if "database is locked" in str(e):
        print("Database is locked. Please make sure no other processes are using it.")
    else:
        print("Error!", e)
finally:
    # Close connection
    conn.close()

# Download and load the model
model_name_or_path = "TheBloke/Llama-2-13B-chat-GGML"
model_basename = "llama-2-13b-chat.ggmlv3.q5_1.bin"

model_path = hf_hub_download(repo_id=model_name_or_path, filename=model_basename)

lcpp_llm = Llama(
    model_path=model_path,
    n_threads=2,
    n_batch=512,
    n_gpu_layers=32
)

print("Llama-2 model loaded successfully!")

# Function to convert natural language to SQL
def nl_to_sql(prompt):
    prompt_template = f"""
    You are an AI assistant that converts natural language questions into SQL queries.

    Database schema:
    Employees(ID, Name, Department, Salary, Hire_Date)
    Departments(ID, Name, Manager)

    Convert the following question into an SQL query:
    Question: {prompt}

    SQL Query:
    """

    response = lcpp_llm(
        prompt=prompt_template,
        max_tokens=150,
        temperature=0.2,
        top_p=0.95,
        repeat_penalty=1.2,
        top_k=100,
        echo=False
    )

    sql_query = response["choices"][0]["text"].strip()

    # Ensure only valid SQL is returned
    if not sql_query.lower().startswith("select"):
        raise ValueError("Invalid SQL generated. Check model output.")

    return sql_query

# Function to convert SQL query results to natural language
def results_to_nl(user_query, sql_results):
    prompt_template = f"""
    You are an AI assistant that converts SQL query results into natural language answers.

    User's Question: {user_query}
    SQL Query Results: {sql_results}
    Provide a clear, concise natural language response:
    """

    response = lcpp_llm(
        prompt=prompt_template,
        max_tokens=150,
        temperature=0.7,
        top_p=0.95,
        repeat_penalty=1.2,
        top_k=100,
        echo=False
    )

    return response["choices"][0]["text"].strip()

# Flask app
app = Flask(__name__)
CORS(app)

# Load the AI model for generating SQL
llm = AutoModelForCausalLM.from_pretrained(
    model_name_or_path,
    model_file=model_basename,
    model_type="llama",
    gpu_layers=50
)

# Function to check if an entity exists in the database
def entity_exists(table, column, value):
    conn = sqlite3.connect("company.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT 1 FROM {table} WHERE {column} = ? LIMIT 1", (value,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

# Function to generate SQL query from natural language
def generate_sql(natural_query):
    if not natural_query or len(natural_query.strip()) == 0:
        return None, "Invalid input. Please provide a valid question."

    prompt = f"Convert this natural language query into a valid SQL SELECT statement: {natural_query}"
    sql_query = llm(prompt).strip()

    # Prevent dangerous queries
    if not sql_query.upper().startswith("SELECT"):
        return None,"""Sorry, I couldn’t understand that. Try asking:
        - 'Show me all employees in the Sales department.'
        - 'Who is the manager of the HR department?'
        - 'List all employees hired after 2022-01-01.'"""

    # Handling common query patterns
    department_query_patterns = {
        r"show me all employees in the (\w+) department": ("employees", "department", "SELECT * FROM employees WHERE department = '{}';"),
        r"who is the manager of the (\w+) department": ("departments", "department", "SELECT manager FROM departments WHERE department = '{}';"),
        r"list all employees hired after (\d{4}-\d{2}-\d{2})": (None, None, "SELECT * FROM employees WHERE hire_date > '{}';"),
        r"list all employees hired before (\d{4}-\d{2}-\d{2})": (None, None, "SELECT * FROM employees WHERE hire_date < '{}';"),
        r"what is the total salary expense for the (\w+) department": ("employees", "department", "SELECT SUM(salary) FROM employees WHERE department = '{}';")
    }

    for pattern, (table, column, query_template) in department_query_patterns.items():
        match = re.match(pattern, natural_query.lower())
        if match:
            entity = match.group(1)
            if table and column and not entity_exists(table, column, entity):
                return None, f"Sorry, The specified {column} '{entity}' does not exist in the database. Please check and try again."
            sql_query = query_template.format(entity)
            return sql_query, None

    return sql_query, "Sorry, I didn’t understand that query. Try again with a valid question."

# Function to execute the SQL query safely
def execute_sql(sql_query):
    conn = sqlite3.connect("company.db")
    cursor = conn.cursor()

    try:
        cursor.execute(sql_query)
        results = cursor.fetchall()

        if not results:
            return None, "No results found. Please check your query and try again."

        return results, None

    except sqlite3.OperationalError as e:
        return None, f"SQL Error: {str(e)}"

    except Exception as e:
        return None, f"Unexpected Error: {str(e)}"

    finally:
        conn.close()

@app.route('/query', methods=['POST'])
def process_query():
    data = request.json
    user_query = data.get("query")

    if not user_query:
        return jsonify({"error": "No query provided. Please enter a valid query."}), 400

    sql_query, sql_error = generate_sql(user_query)

    if sql_error:
        return jsonify({"error": sql_error}), 400

    results, exec_error = execute_sql(sql_query)

    if exec_error:
        return jsonify({"error": exec_error}), 400

    return jsonify({
        "query": sql_query,
        "results": results,
        "message": "Query executed successfully. Here are your results."
    })

if __name__ == '__main__':
    app.run(port=5001)
