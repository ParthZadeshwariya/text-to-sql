import pandas as pd
import matplotlib.pyplot as plt
import uuid
import json
import src.config as config 
from .state import SQLState
from .config import engine, SCHEMA_INFO

def text_to_sql(state: SQLState):
    """
    Convert a natural language query to SQL.
    """
    text = state["text"]
    prompt = f"""You are a SQL expert. Convert the following natural language question into a valid PostgreSQL query.
    
        Database Schema:
        {config.SCHEMA_INFO}

        Question: {text}

        Important Guidelines:
        1. Use only the tables and columns mentioned in the schema.
        2. Use proper JOIN clauses when querying multiple tables.
        3. Return ONLY the SQL query without any explanation or markdown formatting.
        4. If the question contains multiple sub-questions, generate separate SQL queries separated by semicolons.
        5. Use aggregate functions (COUNT, SUM, AVG, etc.) appropriately.
        6. Add LIMIT clauses for queries that might return many rows (default LIMIT 10 unless user specifies).
        7. Use proper WHERE clauses to filter data.
        
        CRITICAL DATE HANDLING RULES:
        8. The date columns (like 'order_purchase_timestamp') are stored as TEXT strings (Format: 'YYYY-MM-DD HH:MM:SS'). 
           - DO NOT use DATE_TRUNC or EXTRACT directly on them.
           - To group by Month: Use SUBSTR(column_name, 1, 7)  (Example: '2017-01')
           - To group by Year: Use SUBSTR(column_name, 1, 4)
           - If you MUST use date comparisons, cast them first: CAST(column_name AS TIMESTAMP).
        
        9. Each SQL statement should be on its own line.

        Generate the SQL query:
        """
    
    iteration = state["iteration"]
    response = config.model.invoke(prompt).content
    return {"query": response, "iteration": iteration + 1}


def execute_query(state: SQLState):
    try:
        engine = config.engine
        query = state['query'].replace("```sql", "").replace("```", "").strip()
        df = pd.read_sql_query(query, engine)
        return {"query_result": df.to_json()}
    except Exception as e:
        return {"error": str(e)}


def analyze_result(state: SQLState):
    result = state['query_result']
    question = state['text']
    visualization_path = state.get('visualization')
    
    instructions = """
    Analyze the result of the query and provide valuable insights for the user.
    Format your response in clear Markdown.
    """

    if visualization_path:
        instructions += """
        \nNOTE: A visualization graph has been generated for this data and will be displayed below your response.
        
        You should refer to the graph in your analysis (e.g., "As shown in the visualization..."), 
        but DO NOT try to embed the image yourself using Markdown tags.
        """

    prompt = f"""
        {instructions}
        
        Question: {question}
        Result: {result}
        
        Provide the final answer now:
    """

    # Get response from LLM
    response = config.model.invoke(prompt).content
    
    return {
        "final_answer": response
    }


def error_solver(state: SQLState):
    error = state["error"]
    text = state["text"]
    query = state["query"]
    iteration = state["iteration"]
    
    if iteration > 3:
        error_msg = f"I apologize, but I'm having trouble generating a correct SQL query. Error: {error}"
        return {
            "final_answer": error_msg, 
            "iteration": iteration + 1
        }
    
    prompt = f"""
        The following SQL query failed with an error. Please fix it.
        {SCHEMA_INFO}
        Original Question: {text}
        Failed SQL Query: {query}
        Error: {error}
        Generate a corrected SQL query. Return ONLY the SQL query:
    """

    response = config.model.invoke(prompt).content
    
    return {
        "query": response,
        "error": None, # Reset error so the loop can try again
        "iteration": iteration + 1
    }


def decide_graph_need(state: SQLState):
    
    question = state["text"]
    result = state["query_result"]
    
    # 1. Safety Check: If there was an error or empty result, skip graph
    if state.get("error") or not result or result == "{}":
        return {"needs_graph": False, "graph_type": "none"}

    # 2. The Prompt
    prompt = f"""
    You are a Data Visualization expert. Analyze the following Question and Data to determine if a visualization would add value.

    Question: {question}
    Data Sample (JSON): {str(result)[:1000]}... 

    Rules:
    - TIMELINES (dates) -> "line"
    - COMPARING CATEGORIES -> "bar"
    - PROPORTIONS/PERCENTAGES -> "pie"
    - CORRELATIONS (X vs Y) -> "scatter"
    - Single numbers or simple text lists -> "none"

    Return ONLY a valid JSON object with no extra text:
    {{
        "needs_graph": true/false,
        "graph_type": "bar/line/pie/scatter/none"
    }}
    """

    # 3. Invoke Model
    response = config.model.invoke(prompt).content
    
    # 4. Clean and Parse JSON
    try:
        # Use the cleaning trick to handle ```json wrappers
        cleaned_response = response.replace("```json", "").replace("```", "").strip()
        decision = json.loads(cleaned_response)
        
        return {
            "needs_graph": decision.get("needs_graph", False),
            "graph_type": decision.get("graph_type", "none")
        }
    except Exception:
        # Fallback default if LLM generates bad JSON
        return {"needs_graph": False, "graph_type": "none"}


def generate_visualization(state: SQLState):
    """
    Generates a unique plot based on the state and saves it with a unique ID.
    """
    if not state.get("needs_graph"):
        return {"visualization": None}

    try:
        df = pd.read_json(state["query_result"])
    except Exception:
        return {"visualization": None}

    # --- PLOTTING LOGIC ---
    plt.figure(figsize=(10, 6))
    plt.clf() # Clear current figure to prevent overlapping data
    
    graph_type = state["graph_type"]
    
    try:
        x_col = df.columns[0] 
        y_col = df.select_dtypes(include=['number']).columns[0]
    except IndexError:
        return {"visualization": None}

    if graph_type == "bar":
        plt.bar(df[x_col].astype(str), df[y_col], color='skyblue')
        plt.xticks(rotation=45, ha='right')
    elif graph_type == "line":
        df = df.sort_values(by=x_col)
        plt.plot(df[x_col].astype(str), df[y_col], marker='o', color='green')
        plt.xticks(rotation=45, ha='right')
    elif graph_type == "pie":
        plt.pie(df[y_col], labels=df[x_col].astype(str), autopct='%1.1f%%')
    elif graph_type == "scatter":
        plt.scatter(df[x_col], df[y_col], alpha=0.5)

    plt.title(f"{y_col} by {x_col}")
    plt.tight_layout()
    
    # --- UNIQUE FILENAME LOGIC ---
    # Create a unique ID (e.g., 'viz_a1b2c3d4.png')
    unique_id = str(uuid.uuid4())[:8] 
    output_path = f"assets/viz_{unique_id}.png"
    
    plt.savefig(output_path)
    plt.close() # Close to free up memory
    
    return {"visualization": output_path}