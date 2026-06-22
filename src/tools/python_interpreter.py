import sys
import io
from langsmith import traceable

@traceable(name="Tool: Python Interpreter")
def execute_python_code(code: str) -> str:
    """Executes a block of Python code and returns its standard output.
    Use this tool to calculate financial metrics, margins, ROE, CAGR, or build forecasts.
    Always print the final result so it can be captured by this tool.
    
    Args:
        code: A valid Python code block to run.
        
    Returns:
        A string containing the printed output or traceback/error message.
    """
    # Create standard output redirects
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    redirected_output = io.StringIO()
    redirected_error = io.StringIO()
    
    sys.stdout = redirected_output
    sys.stderr = redirected_error
    
    # Global/local execution environment
    global_env = {}
    local_env = {}
    
    try:
        # Execute the python script
        exec(code, global_env, local_env)
        
        output = redirected_output.getvalue()
        error = redirected_error.getvalue()
        
        if error:
            return f"Execution succeeded, but warnings/stderr occurred:\n{error}\nOutput:\n{output}"
        return output if output.strip() else "Execution completed successfully with no stdout output. Remember to print your results!"
        
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return f"Execution failed with error: {str(e)}\n\nTraceback:\n{tb}"
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
