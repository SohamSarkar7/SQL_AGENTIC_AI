import streamlit as st
from pathlib import Path
from langchain.agents import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from sqlalchemy import create_engine
import sqlite3
from langchain_groq import ChatGroq


st.set_page_config(page_title="Chat with SQL", page_icon=":guardsman:", layout="wide")
st.title("Chat with SQL")

LOCALDB = "USE_LOCALDB"
MYSQL = "USE_MYSQL"

radio_opt = ["Use SQLLITE 3 Database","Connect to MySQL Database"]
selected_opt= st.sidebar.radio("Select an option", radio_opt)

if radio_opt.index(selected_opt) == 1:
    db_uri = MYSQL
    host = st.sidebar.text_input("Enter MySQL host string")
    user = st.sidebar.text_input("Enter MySQL username")
    password = st.sidebar.text_input("Enter MySQL password", type="password")
    db_name = st.sidebar.text_input("Enter MySQL database name")
    port = st.sidebar.text_input("Enter MySQL port")
else:
    db_uri = LOCALDB


groq_api_key = st.sidebar.text_input("Enter Groq API Key", type="password")


if not db_uri:
    st.info("Please enter a valid database connection string.")

if not groq_api_key:
    st.info("Please enter a valid Groq API Key.")


##LLM model

llm = ChatGroq(api_key=groq_api_key,model_name = "Llama3-8b-8192",streaming= True)



@st.cache_resource(ttl="2h")

def configure_db(db_uri, host=None, user = None, password=None, db_name=None, port=None):
    if db_uri==LOCALDB:
        dbfilepath=(Path(__file__).parent/"example.db").absolute()
        print(dbfilepath)
        creator = lambda: sqlite3.connect(f"file:{dbfilepath}?mode=ro", uri=True)
        return SQLDatabase(create_engine("sqlite:///", creator=creator))
    elif db_uri == MYSQL:
        if not host or not user or not password or not db_name or not port:
            st.error("Please provide all MySQL connection details.")
            st.stop()
        return SQLDatabase(create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"))
    

if db_uri == MYSQL:
    db = configure_db(db_uri, host, user, password, db_name, port)
else:
    db = configure_db(db_uri)
        
## Toolkit

toolkit = SQLDatabaseToolkit(db=db, llm=llm)
agent = create_sql_agent(
    llm = llm,
    toolkit=toolkit,
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION
)

if "messages" not in st.session_state or st.sidebar.button("Clear chat"):

    st.session_state["messages"] = [{"role": "assistant", "content": "Hello! How can I assist you with your SQL queries today?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

user_querry = st.chat_input("Enter your SQL query here:")

if user_querry:
    st.session_state.messages.append({"role": "user", "content": user_querry})
    st.chat_message("user").write(user_querry)

    with st.chat_message("assistant"):
        streamlit_callback = StreamlitCallbackHandler(st.container())
        response = agent.run(user_querry, callbacks=[streamlit_callback])
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.write(response)
