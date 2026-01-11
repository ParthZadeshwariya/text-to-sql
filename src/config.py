import os
import pandas as pd
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy import create_engine

load_dotenv()

db_user = os.getenv("DB_USER") or input("Enter DB_USER: ")
db_password = os.getenv("DB_PASSWORD") or input("Enter DB_PASSWORD: ")
db_host = os.getenv("DB_HOST") or input("Enter DB_HOST: ")
db_port = os.getenv("DB_PORT") or input("Enter DB_PORT: ")
db_name = os.getenv("DB_NAME") or input("Enter DB_NAME: ")

model = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
)

# Create connection
engine = create_engine(f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}")

def get_schema_for_llm():
    print("Loading database schema...")
    schema_query = """
    SELECT table_name, column_name, data_type 
    FROM information_schema.columns 
    WHERE table_schema = 'public' 
    ORDER BY table_name, ordinal_position;
    """
    try:
        df = pd.read_sql_query(schema_query, engine)
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

SCHEMA_INFO = get_schema_for_llm()