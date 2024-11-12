import streamlit as st
from streamlit_ace import st_ace
import tempfile
import ollama
import os
import subprocess
import platform

# Platform-specific g++ command
if platform.system() == "Windows":
    gpp_command = "C:\\msys64\\ucrt64\\bin\\g++.exe"
else:
    gpp_command = "g++"  # For Linux environments like Streamlit Cloud

# Test the g++ installation
try:
    gpp_version = subprocess.check_output([gpp_command, '--version'])
    # st.write(gpp_version.decode())  # Display g++ version in Streamlit app
except FileNotFoundError:
    st.error("g++ is not installed or accessible")


# Set up Java environment variables
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-17-openjdk-amd64"
os.environ["PATH"] += os.pathsep + os.path.join(os.environ["JAVA_HOME"], "bin")

from utils import (
    run_python_code, run_sql_code, format_python_code, format_sql_code,
    optimize_python_code, optimize_code, run_cpp_code, run_java_code,
    format_cpp_code, format_java_code, optimize_cpp_code, optimize_java_code
)

# st.set_page_config(page_title="Coding Platform")

def main_page():
    st.title("PHOENIX - Code Editor")

    languages = ["Python", "SQL", "C++", "Java"]

    if "code" not in st.session_state:
        st.session_state["code"] = ""
    if "custom_input" not in st.session_state:
        st.session_state["custom_input"] = ""
    if "output" not in st.session_state:
        st.session_state["output"] = ""
    if "selected_language" not in st.session_state:
        st.session_state["selected_language"] = "Python"
    if "code_description_response" not in st.session_state:
        st.session_state["code_description_response"] = ""

    def call_run(name):
        result = None
        if name == 'run_button':
            if st.session_state["selected_language"] == "SQL":
                result = run_sql_code(st.session_state["code"])
            elif st.session_state["selected_language"] == "Python":
                result = run_python_code(st.session_state["code"], st.session_state["custom_input"])
            elif st.session_state["selected_language"] == "C++":
                result = run_cpp_code(st.session_state["code"], st.session_state["custom_input"])
            elif st.session_state["selected_language"] == "Java":
                result = run_java_code(st.session_state["code"], st.session_state["custom_input"])
        return result

    def run_func():
        r = call_run('run_button')
        st.session_state["output"] = str(r) if r else "No output produced or an error occurred."
    editor_col, buttons_col = st.columns([3, 1])

    with editor_col:
        col1, col2, col3, col4 = st.columns(4)
        with col2:
            if st.button("Run", key='run_button'):
                run_func()
        with col1:
            if st.button("Help! "):
                st.session_state["current_page"] = "chat"  # Change page to chat page
                st.rerun()  # Trigger rerun to reload the app and navigate to chat page

        with col3:
            def get_file_extension(language):
                if language.lower() == 'python':
                    return ".py"
                elif language.lower() == 'c++':
                    return ".cpp"
                elif language.lower() == 'sql':
                    return ".sql" 
                elif language.lower() == 'java':
                    return ".java"
                else:
                    return ".txt"
            
    
    # Assuming `st.session_state['selected_language']` is already set and contains the language selection
            if st.download_button(
                "Download", 
                data=st.session_state['code'], 
                file_name=f"code{get_file_extension(st.session_state['selected_language'])}", 
                mime="text/plain"
            ):
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=get_file_extension(st.session_state['selected_language']))
                # You can use temp_file here if needed
                # For example, to save the file
                with open(temp_file.name, "w") as f:
                    f.write(st.session_state['code'])


            
            # if st.download_button("Download", data=st.session_state['code'], file_name=f"code.{st.session_state['selected_language'].lower()}", mime="text/plain"):
            #     temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{st.session_state['selected_language'].lower()}")
        with col4:
            if st.button("Submit"):
                st.toast("Success!", icon="✅")
        ##########
                # Code editor
        st.session_state["code"] = st_ace(
            value=st.session_state["code"],
            language=st.session_state["selected_language"].lower() if st.session_state["selected_language"] in ["Python", "SQL"] else "c_cpp" if st.session_state["selected_language"] == "C++" else "java",
            theme="github",
            height=250,
            placeholder="Write your code here..."
        )

    with buttons_col:
        st.session_state["selected_language"] = st.selectbox("Language", languages, index=languages.index(st.session_state["selected_language"]))
        st.session_state["custom_input"]=st.text_input("Custom Input", placeholder="Enter your test cases here...")
        st.text_area("Output", st.session_state["output"], placeholder="Run the code to see output...")

        
    st.sidebar.title("Side Panel")
    
    uploaded_file = st.sidebar.file_uploader("Browse file", type=["py", "sql", "cpp", "java"], label_visibility='collapsed')
    if uploaded_file is not None:
        # Set `st.session_state["code"]` to the uploaded file's content
        st.session_state["code"] = uploaded_file.read().decode("utf-8")
    def format_code():
        if st.session_state["selected_language"] == "SQL":
            st.session_state["code"] = format_sql_code(st.session_state['code'])
        elif st.session_state["selected_language"] == "Python":
            st.session_state["code"] = format_python_code(st.session_state['code'])
        elif st.session_state["selected_language"] == "C++":
            st.session_state["code"] = format_cpp_code(st.session_state['code'])
        elif st.session_state["selected_language"] == "Java":
            st.session_state["code"] = format_java_code(st.session_state['code'])


# Place "Format" and "Optimized" buttons side by side
    col1, col2 = st.sidebar.columns(2)
    with col1:
        format_button = col1.button("Format", on_click=format_code)
    with col2:
        optimize_button = col2.button("Optimized")

    # Add a success toast when the "Optimized" button is clicked
    if optimize_button:
        st.toast("Success!", icon="✅")


    # Display code description response below the button
    with st.sidebar.expander("Code Description"):
        def generate_description(code):
            response = ollama.chat(model='llama3.2:1b', stream=True, messages=[
                {"role": "user", "content": f"Provide a description of the following code in short:\n{code}"}
            ])
            description = ""
            for partial_resp in response:
                token = partial_resp["message"]["content"]
                description += token
            return description

        # Generate code description and update in session state
        description = generate_description(st.session_state["code"])
        st.session_state["code_description_response"] = description
        st.write(st.session_state["code_description_response"])
    col3, col4 = st.sidebar.columns(2)
    with col3:
        col3.button("Language Converter")
    with col4:    
        col4.button("Generate JIRA Tickets")
    # st.sidebar.button("Language Converter")
    # st.sidebar.button("Generate JIRA Tickets")
    st.sidebar.text_area("Feedback",height=20)

    # st.session_state["custom_input"]=st.text_input("Custom Input", placeholder="Enter your test cases here...")
    # st.session_state["custom_input"] = st.text_area("Custom Input",height=5, placeholder="Enter your test cases here...")
def chat_page():
    st.title("Chat with Phoenix")

    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "Phoenix", "content": "How can I help you?"}]

    # Displaying the chat history
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.chat_message(msg["role"], avatar="🧑‍💻").write(msg["content"])
        else:
            st.chat_message(msg["role"], avatar="🤖").write(msg["content"])

    # Handle user input and generate a response
    def generate_response():
        response = ollama.chat(model='llama3.2:1b', stream=True, messages=st.session_state.messages)
        for partial_resp in response:
            token = partial_resp["message"]["content"]
            st.session_state["full_message"] += token
            yield token

    if prompt := st.chat_input():
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user", avatar="🧑‍💻").write(prompt)
        st.session_state["full_message"] = ""
        st.chat_message("Phoenix", avatar="🤖").write_stream(generate_response)
        st.session_state.messages.append({"role": "Phoenix", "content": st.session_state["full_message"]})

    if st.sidebar.button("Back"):
        st.session_state["current_page"] = "home"  # Change page to home
        st.rerun()  # Trigger rerun to reload the app and navigate to the home page


if st.session_state.get("current_page", "home") == "home":
    main_page()
elif st.session_state["current_page"] == "chat":
    chat_page()
