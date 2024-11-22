import io
import sys
import subprocess
import ast
import textwrap
import re
import sqlparse
import sqlite3
import black
import astor
import os
import tempfile
import snowflake.connector
from config import *
import pandas as pd



conn = {
    "user"  : snowflake_user,
    "password": snowflake_password,
    "account": snowflake_account,
    "warehouse": snowflake_warehouse,
    "database": snowflake_database,
    "schema": snowflake_schema
}

connection = snowflake.connector.connect(**conn)


def store_feedback(query):
    print(query)
    cursor = connection.cursor()
    insert_query = f"INSERT INTO PHOENIX_DB.PHOENIX_SC.FEEDBACKS VALUES ('{query}');"
    cursor.execute(insert_query)
    cursor.close()

def store_ticket(task_title,task_description,task_ac,task_assignee,task_status,task_priority,task_comments):
    cursor = connection.cursor()
    # insert_query = f"INSERT INTO PHOENIX_DB.PHOENIX_SC.JIRA_TICKETS(TITLE,DESCRIPTION,ACCEPTANCE_CRITERIA) VALUES ('{task_title}','{task_description}','{task_ac}');"
    # cursor.execute(insert_query)

    insert_query = """
        INSERT INTO PHOENIX_DB.PHOENIX_SC.JIRA_TICKETS
        (TITLE, DESCRIPTION, ACCEPTANCE_CRITERIA,ASSIGNE,STATE,PRIORITY,COMMENTS)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(insert_query, (task_title, task_description, task_ac,task_assignee,task_status,task_priority,task_comments))

    cursor.close()

def fetch_jira_data(j_status):
    cursor = connection.cursor()
    query = "SELECT * FROM PHOENIX_DB.PHOENIX_SC.JIRA_TICKETS WHERE STATE=%s;"
    cursor.execute(query, (j_status,))
    rows = cursor.fetchall()

    # Fetch column names from the cursor
    columns = [col[0] for col in cursor.description]
    cursor.close()
    return pd.DataFrame(rows, columns=columns)
    
def replace_inputs(code, inputs):
    # Extract variable names and optional cast types for input statements in code
    input_vars = extract_inputs(code)
    input_values = [val.strip() for val in inputs.split(",")]

    if len(input_vars) != len(input_values):
        raise ValueError("Number of input variables does not match the number of provided values.")

    # Replace each input() in the code with the corresponding custom input value
    for (var, cast_type), val in zip(input_vars, input_values):
        # Determine the converted value based on the cast type
        try:
            if cast_type == "int":
                converted_val = int(val)
            elif cast_type == "float":
                converted_val = float(val)
            else:
                converted_val = val  # Default to string if no cast is specified
        except ValueError:
            return f"Error: could not convert {val} to {cast_type}"

        # If cast_type is present (like int or float), match with the cast; otherwise, match plain input()
        if cast_type:
            pattern = rf"{re.escape(var)}\s*=\s*{re.escape(cast_type)}\s*\(\s*input\(\s*.*?\)\s*\)"
        else:
            pattern = rf"{re.escape(var)}\s*=\s*input\(\s*.*?\)"

        # Replace matched input with converted value
        code = re.sub(pattern, f"{var} = {repr(converted_val)}", code)

    return code

# Example of the extract_inputs function
def extract_inputs(code):
    # This captures variable names and optional cast types with input()
    return re.findall(r"(\w+)\s*=\s*(\w*)\s*\(?\s*input\(", code)


class CodeOptimizer(ast.NodeTransformer):
    def visit_ListComp(self, node):
        # Convert list comprehensions to generator expressions where appropriate
        return ast.GeneratorExp(
            elt=node.elt,
            generators=node.generators
        )

    def visit_For(self, node):
        # Convert for loops to list comprehensions if applicable
        if isinstance(node.target, ast.Name) and isinstance(node.iter, ast.List):
            return ast.ListComp(
                elt=node.body[0].value,
                generators=[ast.comprehension(target=node.target, iter=node.iter, ifs=[])]
            )
        return self.generic_visit(node)

def optimize_code(source_code):
    # Parse the code into an AST
    tree = ast.parse(source_code)
    
    # Optimize the AST
    optimizer = CodeOptimizer()
    optimized_tree = optimizer.visit(tree)
    
    # Unparse the optimized AST back to source code using astor
    optimized_code = astor.to_source(optimized_tree)
    
    return optimized_code

def run_python_code(code, custom_inputs):
    if extract_inputs(code) and custom_inputs:
        try:
            code = replace_inputs(code, custom_inputs)  # Replace inputs with custom values
        except ValueError as ve:
            return f"Error: {ve}"

    output = io.StringIO()
    sys.stdout = output
    exec_globals = {}
    try:
        exec(code, exec_globals)  # Execute the Python code
        result = output.getvalue()
        return result[:2000]  # Limit output to prevent excessively long responses
    except Exception as e:
        return f"Error during execution: {e}"
    finally:
        sys.stdout = sys.__stdout__

def execute_sql_query(query):
    try:
        connection = sqlite3.connect(":memory:")  # Create an in-memory database
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()  # Commit changes if it's an INSERT/UPDATE/DELETE
        results = cursor.fetchall()  # Fetch results for SELECT queries
        return results
    except Exception as e:
        return f"Error: {e}"
    finally:
        connection.close()  # Ensure the connection is closed

def run_sql_code(code):
    output_df = pd.DataFrame()  # Initialize an empty DataFrame
    # Split the input code into individual SQL statements
    statements = sqlparse.split(code)
    
    try:
        connection = sqlite3.connect(":memory:")  # Create an in-memory database
        cursor = connection.cursor()
        
        for statement in statements:
            statement = statement.strip()  # Clean up whitespace
            if statement:  # Skip empty statements
                cursor.execute(statement)
                connection.commit()  # Commit changes if it's an INSERT/UPDATE/DELETE

                # For SELECT queries, fetch and return results as a DataFrame
                if statement.lower().startswith("select"):
                    columns = [desc[0] for desc in cursor.description]  # Extract column names
                    rows = cursor.fetchall()  # Fetch all rows
                    output_df = pd.DataFrame(rows, columns=columns)  # Convert to DataFrame

        return output_df if not output_df.empty else "No data to display or an error occurred."
    except Exception as e:
        return f"Error: {e}"
    finally:
        connection.close()  # Ensure the connection is closed


def format_python_code(code):
    try:
        return black.format_str(code, mode=black.Mode())
    except Exception as e:
        return f"Error: {e}"

def format_sql_code(code):
    return sqlparse.format(code, reindent=True, keyword_case='upper')

def optimize_python_code(code):
    # Save code to a temporary file with proper format and docstring
    with open("temp_code.py", "w", newline='\n') as file:
        file.write('"""Temporary code for pylint optimization."""\n')  # Adding a module docstring
        file.write(code.replace('\r\n', '\n').strip() + "\n")
    
    # Run pylint on the temporary file
    result = subprocess.run(
        ["pylint", "temp_code.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Clean up the temporary file
    subprocess.run(["del", "temp_code.py"], shell=True)  # Use `rm` for Unix-based systems

    # Check if pylint returned any output
    if result.stdout:
        return result.stdout
    else:
        return "No pylint output or an error occurred: " + result.stderr
    

# Existing classes and functions...

def run_cpp_code(code, custom_input=None):
    with tempfile.TemporaryDirectory() as temp_dir:
        cpp_file_path = os.path.join(temp_dir, "temp_code.cpp")
        exe_file_path = os.path.join(temp_dir, "temp_code.exe")

        # Write the C++ code to a temporary file
        with open(cpp_file_path, "w") as f:
            f.write(code)

        # Compile the C++ code
        compile_result = subprocess.run(
            [
                r"C:\Program Files\Dev-Cpp\MinGW64\bin\g++.exe",
                cpp_file_path,
                "-o",
                exe_file_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Check for compilation errors
        if compile_result.returncode != 0:
            return f"Compilation Error:\n{compile_result.stderr}"

        # Prepare the custom input as newline-separated values
        input_str = "\n".join(custom_input.split(",")) if custom_input else ""

        try:
            # Run the compiled executable
            run_result = subprocess.run(
                [exe_file_path],
                input=input_str,  # Pass inputs as newline-separated values
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )

            # Check for runtime errors
            if run_result.returncode != 0:
                return f"Runtime Error:\n{run_result.stderr}"

            # Parse and format the output to include inputs inline with prompts
            lines = run_result.stdout.splitlines()
            if custom_input:
                inputs = custom_input.split(",")
                formatted_output = []
                input_index = 0

                for line in lines:
                    # Add input values to the prompts
                    if "Enter number" in line and input_index < len(inputs):
                        formatted_output.append(f"{line} {inputs[input_index]}")
                        input_index += 1
                    else:
                        formatted_output.append(line)

                return "\n\n".join(formatted_output)
            else:
                # If no custom input, return raw output
                return run_result.stdout

        except subprocess.TimeoutExpired:
            return "Runtime Error: The program took too long to execute."
        except Exception as e:
            return f"Unexpected error: {e}"
        
        
def run_java_code(code, custom_input=None):
    # Extract the class name from the Java code
    class_match = re.search(r'class\s+(\w+)', code)
    if not class_match:
        return "Error: No class definition found in the code."

    class_name = class_match.group(1)  # Get the class name

    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Path to save the Java file
        java_file_path = os.path.join(temp_dir, f"{class_name}.java")
        
        # Write the Java code to the file
        with open(java_file_path, "w") as f:
            f.write(code)
        
        # Compile the Java code
        compile_result = subprocess.run(
            ["javac", java_file_path],
            capture_output=True,
            text=True,
            cwd=temp_dir  # Set the working directory to temp_dir
        )
        
        # Check for compilation errors
        if compile_result.returncode != 0:
            return f"Compilation error:\n{compile_result.stderr}"
        
        # Format custom input as line-separated values
        formatted_input = custom_input.replace(",", "\n") if custom_input else ""

        # Run the compiled Java code
        try:
            run_result = subprocess.run(
                ["java", class_name],
                input=formatted_input,  # Pass the formatted custom input
                capture_output=True,
                text=True,
                cwd=temp_dir  # Run in the directory where the class file is located
            )
            
            # Check for runtime errors
            if run_result.returncode != 0:
                return f"Runtime error:\n{run_result.stderr}"
            
            # Ensure line-by-line output
            output_lines = run_result.stdout.splitlines()  # Split by lines
            input_values = formatted_input.split("\n")    # Separate input values by lines

            formatted_output = []
            input_index = 0

            # Inject inputs into the prompts line by line
            for line in output_lines:
                if "Enter" in line and ":" in line:  # Detect prompts
                    if input_index < len(input_values):
                        formatted_output.append(f"{line} {input_values[input_index]}")
                        input_index += 1
                    else:
                        formatted_output.append(line)
                else:
                    formatted_output.append(line)

            return "\n\n".join(formatted_output)

        except subprocess.TimeoutExpired:
            return "Runtime Error: The program took too long to execute."
        
        
# Placeholder for C++ formatting function
def format_cpp_code(code):
    # Currently just returns the unmodified code; customize if you add formatting logic
    return code

# Placeholder for Java formatting function
def format_java_code(code):
    # Currently just returns the unmodified code; customize if you add formatting logic
    return code

# Optional: You may also add optimizer placeholders if desired
def optimize_cpp_code(code):
    # Currently just returns the unmodified code; customize if you add optimization logic
    return code

def optimize_java_code(code):
    # Currently just returns the unmodified code; customize if you add optimization logic
    return code
