import streamlit as st
from pathlib import Path
from langchain.agents import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from sqlalchemy import create_engine
import sqlite3
from langchain_groq import ChatGroq
import os
import re
from dotenv import load_dotenv

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

st.set_page_config(page_title="Chat with your Data Source", page_icon=":robot:")
st.title("Chat with your Data Source")

st.markdown("""
    <style>
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        font-size: 18px;
        border-radius: 10px;
        padding: 0.6em 2em;
        border: none;
        cursor: pointer;
        transition: background-color 0.3s;
    }
    .stButton > button:hover {
        background-color: #45a049;
        color: white;
    }
     /* Title (h1) */
    h1 {
        font-size: 25px !important;
    }
    </style>
""", unsafe_allow_html=True)

LOCALDB = "USE LOCALDB"
MYSQL = "USE MYSQL"

radio_opt = ["Upload your own dataset", "Use MySQL database"]

selected_opt = st.sidebar.radio(label="Select Data source", options=radio_opt)

if radio_opt.index(selected_opt) == 1:
    db_uri = MYSQL
    mysql_host = st.sidebar.text_input("Enter MySQL Host")
    mysql_user = st.sidebar.text_input("Enter MySQL User")
    mysql_password = st.sidebar.text_input("Enter MySQL Password", type="password")
    mysql_db = st.sidebar.text_input("Enter MySQL Database")
else:
    db_uri = LOCALDB
    uploaded_file = st.sidebar.file_uploader("Upload your CSV file here", type=["csv"], accept_multiple_files=False)
    st.sidebar.caption("💡 Tip: Make sure your file has headers in the first row.")
    if_not_exists = st.sidebar.radio("If table exists", options=["append", "replace"], index=0, 
                                    help="Append = Add new records to the data source | Replace = Drop and recreate the data source")
    table_name = st.sidebar.text_input("Enter name for the data source", value="")
    if st.sidebar.button("Upload & Save to DB", key="upload_btn"):
        if not uploaded_file:
            st.sidebar.error("Please upload a CSV file to proceed.")
        elif not table_name:
            st.sidebar.error("Please enter a name for the data source.")
        else:
            from upload_dataset import upload_dataset
            db_path = (Path(__file__).parent / "student.db").absolute()
            result_msg = upload_dataset(uploaded_file, table_name, db_path, if_not_exists)
            if "successfully" in result_msg:
                st.sidebar.success(result_msg)
            else:
                st.sidebar.error(result_msg)

if not db_uri:
    st.info("Please select a data source.")

llm = ChatGroq(groq_api_key=groq_api_key, model_name="meta-llama/llama-4-maverick-17b-128e-instruct", streaming=False)

@st.cache_resource(ttl="2h")
def configure_db(db_uri, mysql_host=None, mysql_user=None, mysql_password=None, mysql_db=None):
    if db_uri == LOCALDB:
        db_file_path = (Path(__file__).parent / "student.db").absolute()
        #print(f"Using SQLite DB at: {db_file_path}")
        creator = lambda: sqlite3.connect(f"file:{db_file_path}?mode=ro", uri=True)
        return SQLDatabase(create_engine("sqlite://", creator=creator))
    elif db_uri == MYSQL:
        if not all([mysql_host, mysql_user, mysql_password, mysql_db]):
            st.error("Please provide all MySQL connection details.")
            st.stop()
        return SQLDatabase(create_engine(f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}"))
    
if db_uri==MYSQL:
    db = configure_db(db_uri, mysql_host, mysql_user, mysql_password, mysql_db)
else:
    db = configure_db(db_uri)

toolkit = SQLDatabaseToolkit(db=db, llm=llm, verbose=False)

agent=create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=False,
    top_k=10000000000000000
)

if "messages" not in st.session_state or st.sidebar.button("Clear message history"):
    st.session_state["messages"] = [{"role": "assistant", "content": "Hi, I am RJ! How can I help you?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

user_query = st.chat_input(placeholder="Ask me anything about your data...")

NO_RESULT_PATTERNS = [
    r"\bi don('?t| not)\b",         # "I don't" / "I do not"
    r"couldn('?t| not) find\b",     # couldn't find / could not find
    r"\bno results?\b",
    r"\bnot found\b",
    r"\bcan't find\b",
    r"\bdidn't find\b",
    r"\bunable to find\b",
]

def is_no_result_text(text: str) -> bool:
    if not text:
        return True
    t = text.lower()
    # quick heuristics: short/empty answers are likely failures
    if len(t.strip()) < 10:
        return True
    for p in NO_RESULT_PATTERNS:
        if re.search(p, t):
            return True
    return False

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    st.chat_message("user").write(user_query)

    with st.chat_message("assistant"):
        with st.spinner("Working on the query..."):
            try:
                response = agent.run(user_query)
            except Exception as e:
                # log or expose more details for debugging if you want:
                st.error("Agent execution error.")
                st.error(f"Error details: {e}")
                custom_msg = (
                    "I couldn't find any relevant information for that query. Something went wrong. Please try again "
                )
                st.session_state.messages.append({"role": "assistant", "content": custom_msg})
                st.write(custom_msg)
            else:
                if is_no_result_text(response):
                    custom_msg = (
                        "I couldn't find relevant data for your query. \n"
                        "Following are the available tables in your system"
                    )
                    st.session_state.messages.append({"role": "assistant", "content": custom_msg})
                    st.write(custom_msg)
                    tables = db.get_usable_table_names()
                    for i in range(len(tables)):
                        st.write(f"{tables[i]}\n")
                else:
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.write(response)
