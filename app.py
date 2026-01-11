import os
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from src.graph import build_graph
import src.config as app_config  # Importing the config module to modify it dynamically

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AI SQL Agent",
    page_icon="📊",
    layout="wide"
)

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .stChatInput {border-radius: 20px;}
    .block-container {padding-top: 2rem;}
    .stButton button {width: 100%; border-radius: 10px;}
    div[data-testid="stExpander"] {border: none; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);}
    div[data-testid="stStatusWidget"] {border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: DATABASE CONNECTION ---
with st.sidebar:
    st.title("🔌 Connect Database")
    
    # 1. API Key Setup
    with st.expander("🔑 LLM Settings", expanded=False):
        api_key = st.text_input("Google API Key", type="password")
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
            # Reload model if needed, but usually env var is enough for next invoke

    # 2. Database Connection Form
    with st.form("db_connection"):
        st.subheader("PostgreSQL Credentials")
        host = st.text_input("Host", value="localhost")
        port = st.text_input("Port", value="5432")
        user = st.text_input("Username", value="postgres")
        password = st.text_input("Password", type="password")
        dbname = st.text_input("Database Name", value="ecommerce_db")
        
        connect_btn = st.form_submit_button("Connect", type="primary")

    # 3. Connection Logic
    if "db_status" not in st.session_state:
        st.session_state.db_status = False

    if connect_btn:
        try:
            # Construct Connection URI
            db_uri = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
            new_engine = create_engine(db_uri)
            
            # Test Connection
            with new_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            # --- GLOBAL OVERRIDE ---
            # This is the key step: We update the global variables in src.config
            app_config.engine = new_engine
            app_config.SCHEMA_INFO = app_config.get_schema_for_llm(new_engine)
            
            st.session_state.db_status = True
            st.success(f"✅ Connected to {dbname}!")
            
        except Exception as e:
            st.session_state.db_status = False
            st.error(f"❌ Connection Failed: {e}")

    # 4. Show Status
    if st.session_state.db_status:
        st.divider()
        st.caption(f"Connected: **{dbname}**")
        with st.expander("📂 View Loaded Schema"):
            st.code(app_config.SCHEMA_INFO, language="text")

# --- MAIN CHAT INTERFACE ---
st.title("📊 Enterprise SQL Agent")
st.caption("Ask questions about your data. I can generate SQL, fix errors, and visualize results.")

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! Please connect your database in the sidebar to get started."}
    ]

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("image"):
            st.image(msg["image"])

# Handle User Input
if prompt := st.chat_input("Ex: Show me the monthly revenue trend for 2017..."):
    
    # 1. Validation
    if not st.session_state.db_status:
        st.error("Please connect to a database first (Sidebar)!")
        st.stop()

    # 2. Append User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 3. Process with AI Agent
    with st.chat_message("assistant"):
        status_container = st.status("🧠 Processing...", expanded=True)
        
        try:
            # Initialize Graph
            app = build_graph()
            inputs = {"text": prompt, "iteration": 0}
            
            final_state = {}
            
            # Stream events to show progress
            for step in app.stream(inputs):
                node_name = list(step.keys())[0]
                status_container.write(f"⚙️ Executing: **{node_name}**")
                final_state.update(step[node_name])
            
            status_container.update(label="✅ Analysis Complete!", state="complete", expanded=False)
            
            # 4. Display Final Result
            if final_state:
                final_response = final_state.get("final_answer", "No answer generated.")
                # Check for Visualization

                query =final_state.get("query")
                if query:
                    st.markdown(query)

                image_path = final_state.get("visualization")
                if image_path:
                    st.image(image_path)
                
                # Display Query Result
                query_result = final_state.get("query_result")
                if query_result:
                    try:
                        # query_result is a JSON string from df.to_json()
                        df_result = pd.read_json(query_result)
                        with st.expander("📊 Query Result Data", expanded=False):
                            st.dataframe(df_result)
                    except ValueError:
                        st.write(query_result)
                    
                st.markdown(final_response)
                
                
                # Save to History
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": final_response,
                    "image": image_path
                })
            else:
                st.error("Workflow failed to return a final state.")
                
        except Exception as e:
            status_container.update(label="❌ Error", state="error")
            st.error(f"An error occurred: {e}")