import streamlit as st
from streamlit_ace import st_ace
import tempfile
import ollama
import pandas as pd
import subprocess
from utils2 import (
    run_python_code, run_sql_code, format_python_code, format_sql_code,
    optimize_python_code, optimize_code, run_cpp_code, run_java_code,
    format_cpp_code, format_java_code, optimize_cpp_code, optimize_java_code,
    store_feedback,store_ticket,fetch_jira_data
)

st.set_page_config(layout="wide",page_icon='🐦')

if 'task' not in st.session_state:
    st.session_state['task'] = 'No task Specified'

if 'task_title' not in st.session_state:
    st.session_state['task_title'] = 'No task Specified'

if 'task_description' not in st.session_state:
    st.session_state['task_description'] = 'No task Specified'

if 'task_ac' not in st.session_state:
    st.session_state['task_ac'] = 'No task Specified'

def generate_task_title(code):
    response = ollama.chat(model='llama3.2:1b', stream=True, messages=[
        {"role": "user", "content": f"Provide one best title without any explanation or description for the task :\n{code}"}
    ])
    description = ""
    for partial_resp in response:
        token = partial_resp["message"]["content"]
        description += token
    return description

def generate_task_description(code):
    response = ollama.chat(model='llama3.2:1b', stream=True, messages=[
        {"role": "user", "content": f"Provide a description of the following task in short:\n{code}"}
    ])
    description = ""
    for partial_resp in response:
        token = partial_resp["message"]["content"]
        description += token
    return description

def generate_task_ac(code):
    response = ollama.chat(model='llama3.2:1b', stream=True, messages=[
        {"role": "user", "content": f"Provide an acceptance criteria with sample input and output without any code for the following task :\n{code}"}
    ])
    description = ""
    for partial_resp in response:
        token = partial_resp["message"]["content"]
        description += token
    return description

def display_jira_data(status):
    try:
        df = fetch_jira_data(status)
        if df.empty:
            st.warning("No Tickets are present in this Section.")
        else:
            if 'TITLE' not in df.columns:
                st.error("The table must have a 'TITLE' column to use as expander headers.")
                return
            for _, row in df.iterrows():
                title = row['TITLE']
                with st.expander(f"{title}"):
                    for column, value in row.items():
                        st.write(f"**{column}:** {value}")

    except Exception as e:
        st.error(f"Error fetching data: {e}")

def run_ollama(prompt):
    """
    Use the Ollama CLI to generate a response from the model.
    """
    try:
        process = subprocess.Popen(
            ["ollama", "run", "codegemma:7b"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True  # Ensures UTF-8 encoding
        )
        
        stdout, stderr = process.communicate(input=prompt)

        if stderr:
            print(f"Error from Ollama CLI: {stderr.strip()}")
            return None

        return stdout.strip()
    except Exception as e:
        print(f"An error occurred: {e}")
        return None      

def display_output(result):
    if isinstance(result, pd.DataFrame):
        if result.empty:
            st.session_state["output"] = "The result DataFrame is empty."
        else:
            # Display as DataFrame if it's too large, provide an option to view more
            st.session_state["output"] = result
            #st.write(result)
            # Optionally display a message if it's large
            #if result.shape[0] > 20 or result.shape[1] > 10:  # Adjust size as per need
                #st.write("Note: This is a large table. You can scroll for more data.")
    elif isinstance(result, str):
        st.session_state["output"] = result
    elif isinstance(result, (int, float)):
        st.session_state["output"] = f"Output: {result}"
    else:
        # For unsupported types, just show the type
        st.session_state["output"] = f"Unsupported output type: {type(result)}"

def main_page(): 
    st.markdown("<h1 style='text-align: center;'>Phoenix</h1>", unsafe_allow_html=True)
    st.markdown("<h3>Welcome!</h3>", unsafe_allow_html=True)

    st.session_state["task"] = st.text_area("What are your plans for this session ?", placeholder="Describe your tasks or goals for today...")
    col11, col12,col3 = st.columns(3)
    with col11:
        if st.button("Generate ticket"):
            if st.session_state["task"] != '':
                st.session_state['task_title'] = generate_task_title(st.session_state["task"])
                st.session_state['task_description'] = generate_task_description(st.session_state["task"])
                st.session_state['task_ac'] = generate_task_ac(st.session_state["task"])

                with st.expander("TICKET"):
                    st.write(st.session_state['task_title'])
                    st.markdown("<h6>Description</h6>", unsafe_allow_html=True)
                    st.write(st.session_state['task_description'])
                    st.markdown("<h6>Acceptance criteria</h6>", unsafe_allow_html=True)
                    st.write(st.session_state['task_ac'])
                    st.session_state["show_editor_button"] = True

                    store_ticket( st.session_state['task_title'],st.session_state['task_description'],st.session_state['task_ac'],'UNASSIGNED','TO DO','MEDIUM','')

            else:
                st.error("Please enter some description to generate a ticket")
    with col12:
        if st.button("View Tickets"):
            st.session_state["current_page"] = "Jira2"  # Change page to home
            st.rerun()  # Trigger rerun to reload the app and navigate to the home page
    with col3:
        if st.button("Go to Editor"):
            st.session_state["current_page"] = "first"  # Set the current page to editor
            st.rerun()  # Trigger rerun to navigate to the editor page

        if st.session_state.get("current_page") == "first":
            first_page()  # Function that defines the editor page
  

def first_page():
    if st.sidebar.button("Back"):
        st.session_state["current_page"] = "home"  # Change page to home
        st.rerun()  # Trigger rerun to reload the app and navigate to the home page

    st.title("🐦 PHOENIX - Code Editor",)

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
    if "conversion_language" not in st.session_state:
        st.session_state["conversion_language"] = ""
        
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
        # st.session_state["output"] = str(r) if r else "No output produced or an error occurred."
        display_output(r)
    
    editor_col, buttons_col = st.columns([3, 1])

    with editor_col:
        col1, col2, col3, col4,col5 = st.columns(5)
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
            
            if st.download_button(
                "Download", 
                data=st.session_state['code'], 
                file_name=f"code{get_file_extension(st.session_state['selected_language'])}", 
                mime="text/plain"
            ):
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=get_file_extension(st.session_state['selected_language']))
                with open(temp_file.name, "w") as f:
                    f.write(st.session_state['code'])

        with col4:
            if st.button("Submit"):
                st.toast("Success!", icon="✅")

        with col5:
            st.session_state["custom_input"]=st.text_input("Custom Input", placeholder="Enter your test cases here...")

        st.session_state["code"] = st_ace(
            value=st.session_state["code"],
            language=st.session_state["selected_language"].lower() if st.session_state["selected_language"] in ["Python", "SQL"] else "c_cpp" if st.session_state["selected_language"] == "C++" else "java",
            theme="github", #theme="monokai"
            height=250,
            placeholder="Write your code here...",
            key="editor"
        )

        with buttons_col:
            st.session_state["selected_language"] = st.selectbox("Language", languages, index=languages.index(st.session_state["selected_language"]))
            # st.session_state["custom_input"]=st.text_input("Custom Input", placeholder="Enter your test cases here...")
            # st.text_area("Output", st.session_state["output"], placeholder="Run the code to see output...")
            with st.expander("Code Description"):
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
            
            with st.expander("Language Converter"):
                if st.session_state["code"]:
                    if st.button("Python"):
                        prompt = f"Convert the following {st.session_state['selected_language']} code to Python:\n{st.session_state['code']}"
                        converted_code = run_ollama(prompt)
                        st.session_state["converted_code"] = converted_code
                    if st.button("java"):
                        prompt = f"Convert the following {st.session_state['selected_language']} code to java which can executable:\n{st.session_state['code']}"
                        converted_code = run_ollama(prompt)
                        st.session_state["converted_code"] = converted_code
                    if st.button("c++"):
                        prompt = f"Convert the following {st.session_state['selected_language']} code to c++ which can executable:\n{st.session_state['code']}"
                        converted_code = run_ollama(prompt)
                        st.session_state["converted_code"] = converted_code
                    if st.button("sql"):
                        prompt = f"Convert the following {st.session_state['selected_language']} code to sql:\n{st.session_state['code']}"
                        converted_code = run_ollama(prompt)
                        st.session_state["converted_code"] = converted_code
                else:
                    st.warning("Please enter some code to convert.")    
            
            col1,col2 = st.columns(2)
            with col1:
                suggest_code = st.button("Suggest code")
                if suggest_code:
                    st.toast("Success!",icon="✅")
            with col2:
                test_case = st.button("Test Cases")
                if test_case:
                    st.toast("Success!",icon="✅")
                    
            col3,col4 = st.columns(2)
            with col3:
                optimize_button = st.button("Optimized")
                if optimize_button:
                    st.toast("Success!", icon="✅")
            with col4:
                fix_code = st.button("Fix Code")
                if fix_code:
                    st.toast("Success!", icon="✅")
                    
            code_compt=st.button("Code Completion")
            if code_compt:
                st.toast("Success!", icon="✅")      
        
    # st.session_state["custom_input"]=st.text_input("Custom Input", placeholder="Enter your test cases here...")
    st.write("Output:")
    if "output" in st.session_state:
        st.write(st.session_state["output"])
    
    uploaded_file = st.sidebar.file_uploader("Browse file", type=["py", "sql", "cpp", "java"], label_visibility='collapsed')
    if uploaded_file is not None:
        st.session_state["code"] = uploaded_file.read().decode("utf-8")
       
    with st.sidebar.expander("Ticket"):
        st.write(st.session_state['task_title'])
        st.markdown("<h3>Description</h3>", unsafe_allow_html=True)
        st.write(st.session_state['task_description'])
        st.markdown("<h3>Acceptance criteria</h3>", unsafe_allow_html=True)
        st.write(st.session_state['task_ac']) 
    

    def format_code():
        if st.session_state["selected_language"] == "SQL":
            st.session_state["code"] = format_sql_code(st.session_state['code'])
        elif st.session_state["selected_language"] == "Python":
            st.session_state["code"] = format_python_code(st.session_state['code'])
        elif st.session_state["selected_language"] == "C++":
            st.session_state["code"] = format_cpp_code(st.session_state['code'])
        elif st.session_state["selected_language"] == "Java":
            st.session_state["code"] = format_java_code(st.session_state['code'])

    # col1, col2 = st.sidebar.columns(2)
    # with col1:
    #     format_button = col1.button("Format", on_click=format_code)
    # with col2:
    #     optimize_button = col2.button("Optimized")
        
    # if optimize_button:
    #     st.toast("Success!", icon="✅")


    st.session_state["converted_code"] = ''    
    col3, col4 = st.sidebar.columns(2)
    with col3:
        pass
    with col4:    
        if st.button("JIRA"):
            st.session_state["current_page"] = "Jira"  # Change page to chat page
            st.rerun()    
        if st.button("JIRA 2"):
            st.session_state["current_page"] = "Jira2"  # Change page to chat page
            st.rerun()      
    
    if st.session_state["converted_code"]!='':
            with st.sidebar.expander("Converted Code", expanded=True):
                st.code(st.session_state["converted_code"], language=("Python").lower())
              
    with st.sidebar.popover("feedback"):
        feedback_received_2 = 0
        st.markdown("👋 Hello, Please enter your Feedback here")
        feedback_received = st.text_area("")
        if(st.button("ok")):
            if(feedback_received):
                store_feedback(feedback_received)
                feedback_received_2 = 1
        if(feedback_received_2 == 1):
            st.success("Thank you for your feedback")

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
        st.session_state["current_page"] = "first"  # Change page to home
        st.rerun()  # Trigger rerun to reload the app and navigate to the home page

def gen_jira_page():
    st.title("Generate Jira Tickets")
    if st.sidebar.button("Back"):
        st.session_state["current_page"] = "home"  # Change page to home
        st.rerun()  # Trigger rerun to reload the app and navigate to the home page

    # Sample data to represent JIRA tickets
    data = {
        "Ticket ID": ["JIRA-001", "JIRA-002", "JIRA-003", "JIRA-004"],
        "Title": ["Bug in login page", "Add feature X", "Improve performance", "Update documentation"],
        "Assignee": ["Alice", "Bob", "Charlie", "David"],
        "Status": ["To Do", "In Progress", "Review", "Done"],
        "Priority": ["High", "Medium", "Low", "Medium"],
        "Description": [
            "Login page bug causing error 500.",
            "Add new feature X to improve UX.",
            "Optimize database queries for better performance.",
            "Update documentation to reflect recent changes."
        ]
    }

    df = pd.DataFrame(data)
    st.title("JIRA-like Task Dashboard")
    st.sidebar.header("Filter Tasks")

    status_filter = st.sidebar.multiselect("Status", options=df["Status"].unique(), default=df["Status"].unique())
    priority_filter = st.sidebar.multiselect("Priority", options=df["Priority"].unique(), default=df["Priority"].unique())

    filtered_df = df[(df["Status"].isin(status_filter)) & (df["Priority"].isin(priority_filter))]

    st.subheader("Tasks")
    for _, row in filtered_df.iterrows():
        with st.expander(f"{row['Ticket ID']}: {row['Title']}"):
            st.write(f"**Assignee:** {row['Assignee']}")
            st.write(f"**Status:** {row['Status']}")
            st.write(f"**Priority:** {row['Priority']}")
            st.write(f"**Description:** {row['Description']}")

    with st.sidebar.expander("Create New Task"):
        new_title = st.text_input("Task Title")
        new_assignee = st.text_input("Assignee")
        new_status = st.selectbox("Status", options=["To Do", "In Progress", "Review", "Done"])
        new_priority = st.selectbox("Priority", options=["High", "Medium", "Low"])
        new_description = st.text_area("Description")

        if st.button("Add Task"):
            # Add new task to dataframe
            new_task = pd.DataFrame({
                "Ticket ID": [f"JIRA-{len(df)+1:03}"],
                "Title": [new_title],
                "Assignee": [new_assignee],
                "Status": [new_status],
                "Priority": [new_priority],
                "Description": [new_description]
            })
            df = pd.concat([df, new_task], ignore_index=True)
            st.success("Task added successfully!")
            
    st.subheader("Task Overview")
    st.dataframe(df)

def gen_jira_page2():
    st.title("Generate Jira Tickets")
    if st.sidebar.button("Back To Home"):
        st.session_state["current_page"] = "home"  # Change page to home
        st.rerun()  # Trigger rerun to reload the app and navigate to the home page

    if st.sidebar.button("Go To Editor"):
        st.session_state["current_page"] = "first"  # Change page to home
        st.rerun()  # Trigger rerun to reload the app and navigate to the home page

    with st.sidebar.expander("Create New Task"):
        new_title = st.text_input("Task Title")
        new_assignee = st.text_input("Assignee")
        new_status = st.selectbox("Status", options=["TO DO", "DEV", "QA", "DONE"])
        new_priority = st.selectbox("Priority", options=["High", "Medium", "Low"])
        new_description = st.text_area("Description")
        new_ac = st.text_area("Acceptance Criteria")
        new_comments = st.text_area("Comments")

        if st.button("Add Task"):
            store_ticket(new_title,new_description,new_ac,new_assignee,new_status,new_priority,new_comments)
            st.success("Task added successfully!")
            st.rerun()
                
    col1, col2= st.columns([1,4])
    with col1:
        st.text_input('search')
    with col2:
        person = st.selectbox("filter on people",('Anu','Rohith','Surendra'))
    col3,col4,col5,col6=st.columns(4)
    with col3:
        st.write("TO DO")
        display_jira_data('TO DO')

    with col4:
        st.write("DEV")
        display_jira_data('DEV')
    with col5:
        st.write("QA")
        display_jira_data('QA')
    with col6:
        st.write("DONE")
        display_jira_data('DONE')


if st.session_state.get("current_page", "home") == "home":
    main_page()
elif st.session_state["current_page"] == "first":
    first_page()
elif st.session_state["current_page"] == "chat":
    chat_page()
elif st.session_state["current_page"] == "Jira":
    gen_jira_page()
elif st.session_state["current_page"] == "Jira2":
    gen_jira_page2()