import json
import tempfile
import csv
import streamlit as st
import pandas as pd
# from agno.models.openai import OpenAIChat
from phi.agent.duckdb import DuckDbAgent
from phi.tools.pandas import PandasTools
import re

from phi.model.openai import OpenAIChat

pdTools = PandasTools()

def preprocess_and_save(file):
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file,encoding='utf-8',na_values=['NA','N/A','missing'])
        elif file.name.endswith('.xlsx'):
            df = pd.read_excel(file,na_values=['NA','N/A','missing'])
        else:
            st.error("Unsupported file format. Please upload CSV or Excel file.")
            return None,None,None
        
        for col in df.select_dtypes(include=['object']):
            df[col] = df[col].astype(str).replace({r'"' : '""'}, regex=True)

        for col in df.columns:
            if 'date' in col.lower():
                df[col] = pd.to_datetime(df[col],errors='coerce')
            elif df[col].dtype == 'object':
                try:
                    df[col] = pd.to_numeric(df[col])
                except (ValueError,TypeError) :
                    pass

        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
            temp_path = temp_file.name
            df.to_csv(temp_path, index=False, quoting=csv.QUOTE_ALL)

        return temp_path, df.columns.to_list(), df

    except Exception as e:
        st.error(f"Error processing file: {e}")
        return None, None, None


st.title("📊 Data Analyst Agent")

with st.sidebar:
    st.header("API Keys")
    openai_key = st.text_input("Enter your OpenAI API Key", type="password")
    if openai_key:
        st.session_state.openai_key = openai_key
        st.success("API Key saved")
    else:
        st.warning("Please enter your OpenAI API key to proceed")

uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv","xlsx"])


if uploaded_file is not None and "openai_key" in st.session_state:
    temp_path,columns,df = preprocess_and_save(uploaded_file)

    if temp_path and columns and df is not None:
        # Display the uploaded data as a table
        st.write("Uploaded Data:")
        st.dataframe(df) # Use st.dataframe for an interactive table

        # Display the columns of the uploaded data
        st.write("Uploaded columns:", columns)

        # Configure the semantic model with the temporary file path
        semantic_model = {
            "tables": [
                {
                    "name" : "uploaded_data",
                    "description": "Contains the uploaded dataset.",
                    "path": temp_path,
                }
            ]
        }

        duckdb_agent = DuckDbAgent(
            model=OpenAIChat(model="gpt-4", api_key=st.session_state.openai_key),
            semantic_model=json.dumps(semantic_model),
            tools=[PandasTools()],
            markdown=True,
            add_history_to_messages=False,
            followups=False,
            read_tool_call_history=False,  
            system_prompt="You are an expert data analyst. Generate SQL queries to solve the user's query Return only the SQL query, enclosed in ```sql ``` and give the final answer."
        )

        if "generated_code" not in st.session_state:
            st.session_state.generated_code = None

        user_query = st.text_area("Ask a query about the data:")

        # Add info message about terminal output
        st.info("💡 Check your terminal for a clearer output of the agent's response")

        if st.button("Submit Query"):
            if user_query.strip() == "":
                st.warning("Please enter a query")
            else:
                try:
                    with st.spinner("Processing your query"):
                        # Get the response from DuckDbAgent

                        response1 = duckdb_agent.run(user_query)

                        if hasattr(response1, 'content'):
                            response_content = response1.content

                        else:
                            response_content = response1.content

                        response = duckdb_agent.print_response(
                            user_query,
                            stream=True,
                        )

                    # Display the response in streamlit
                    st.markdown(response_content)

                except Exception as e:
                    st.error(f"Error generating response from the DuckDbAgent: {e}")
                    st.error("Please try rephrasing your query or check if the data format is correct.")



