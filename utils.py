import io
import sys
import subprocess
import ast
import re
import sqlparse
import sqlite3
import black
import astor
import os
import tempfile


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

def run_python_code(code,custom_input=None):
    output = io.StringIO()
    sys.stdout = output  # Redirect stdout to capture print output

    exec_globals = {}
    try:
        exec(code, exec_globals)
        return output.getvalue() if output.getvalue() else "No output produced."
    except Exception as e:
        return f"Error during execution: {e}"
    finally:
        sys.stdout = sys.__stdout__  # Reset redirect.

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

def run_sql_code(code,custom_input=None):
    output = []
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
                if statement.lower().startswith("select"):
                    results = cursor.fetchall()  # Fetch results for SELECT queries
                    output.append(results)
        return output
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


import subprocess

def run_cpp_code(code, custom_input=None):
    # Write the C++ code to a temporary file
    with open("temp_code.cpp", "w") as f:
        f.write(code)
    
    # Compile the C++ code using the 'g++' command available in the system's PATH
    compile_result = subprocess.run(
        ["g++", "temp_code.cpp", "-o", "temp_code.out"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    
    # Check if there were compilation errors and print the error details
    if compile_result.returncode != 0:
        print("Compilation Error Details:", compile_result.stderr)  # Print detailed error message
        return f"Compilation Error: {compile_result.stderr}"
    
    # Ensure the compiled output is executable
    os.chmod("temp_code.out", 0o755)  # Make the output file executable
    
    # Run the compiled output, suppressing the version info of g++
    run_result = subprocess.run(
        ["./temp_code.out"],  # Use './' to indicate it's a local executable
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    
    # Only show the runtime output if there is no error
    if run_result.returncode == 0:
        return run_result.stdout
    else:
        return f"Runtime Error: {run_result.stderr}"
def run_java_code(code, input_data):
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
            ["javac", f"{class_name}.java"],
            capture_output=True,
            text=True,
            cwd=temp_dir  # Set the working directory to temp_dir
        )
        
        # Check for compilation errors
        if compile_result.returncode != 0:
            return f"Compilation error:\n{compile_result.stderr}"
        
        # Run the compiled Java code
        run_result = subprocess.run(
            ["java", class_name],
            capture_output=True,
            text=True,
            cwd=temp_dir  # Run in the directory where the class file is located
        )
        
        # Check for runtime errors or return output
        if run_result.returncode != 0:
            return f"Runtime error:\n{run_result.stderr}"
        
        return run_result.stdout
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

