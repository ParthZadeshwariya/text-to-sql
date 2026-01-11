import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy import create_engine

# Initialize with a dummy or None. We will overwrite this from app.py
engine = None 

# LLM Setup
model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

# Schema Loader (Now accepts an engine argument)
def get_schema_for_llm(target_engine):
    if not target_engine:
        return "No database connected."
        
    print("Loading database schema...")
    schema_query = """
    SELECT table_name, column_name, data_type 
    FROM information_schema.columns 
    WHERE table_schema = 'public' 
    ORDER BY table_name, ordinal_position;
    """
    try:
        df = pd.read_sql_query(schema_query, target_engine)
        schema_text = "Database Schema:\n\n"
        for table in df['table_name'].unique():
            schema_text += f"Table: {table}\n"
            table_cols = df[df['table_name'] == table]
            for _, row in table_cols.iterrows():
                schema_text += f"  - {row['column_name']} ({row['data_type']})\n"
            schema_text += "\n"
        return schema_text
    except Exception as e:
        return f"Error loading schema: {e}"

# Global variable to store schema string
SCHEMA_INFO = ""