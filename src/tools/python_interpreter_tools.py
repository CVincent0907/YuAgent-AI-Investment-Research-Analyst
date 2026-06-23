# import sys
# import io
# from langsmith import traceable

# @traceable(name="Tool: Python Interpreter")
# def execute_python_code(code: str) -> str:
#     """Executes a block of Python code and returns its standard output.
#     Use this tool to calculate financial metrics, margins, ROE, CAGR, or build forecasts.
#     Always print the final result so it can be captured by this tool.
    
#     Args:
#         code: A valid Python code block to run.
        
#     Returns:
#         A string containing the printed output or traceback/error message.
#     """
#     # Create standard output redirects
#     old_stdout = sys.stdout
#     old_stderr = sys.stderr
#     redirected_output = io.StringIO()
#     redirected_error = io.StringIO()
    
#     sys.stdout = redirected_output
#     sys.stderr = redirected_error
    
#     # Global/local execution environment
#     global_env = {}
#     local_env = {}
    
#     try:
#         # Execute the python script
#         exec(code, global_env, local_env)
        
#         output = redirected_output.getvalue()
#         error = redirected_error.getvalue()
        
#         if error:
#             return f"Execution succeeded, but warnings/stderr occurred:\n{error}\nOutput:\n{output}"
#         return output if output.strip() else "Execution completed successfully with no stdout output. Remember to print your results!"
        
#     except Exception as e:
#         import traceback
#         tb = traceback.format_exc()
#         return f"Execution failed with error: {str(e)}\n\nTraceback:\n{tb}"
#     finally:
#         sys.stdout = old_stdout
#         sys.stderr = old_stderr


import sys
import io
import contextlib
import signal
from langsmith import traceable

_SAFE_BUILTINS = {
    "print": print, "range": range, "len": len, "enumerate": enumerate,
    "zip": zip, "map": map, "filter": filter, "sorted": sorted,
    "sum": sum, "min": min, "max": max, "abs": abs, "round": round,
    "int": int, "float": float, "str": str, "bool": bool, "list": list,
    "dict": dict, "tuple": tuple, "set": set, "isinstance": isinstance,
    "type": type, "repr": repr, "hasattr": hasattr, "getattr": getattr,
    "ValueError": ValueError, "TypeError": TypeError, "Exception": Exception,
    "__import__": __import__,  # needed for: import math, etc.
}

def _timeout_handler(signum, frame):
    raise TimeoutError("Code execution exceeded time limit")

@traceable(name="Tool: Python Interpreter")
def execute_python_code(code: str, timeout_seconds: int = 10) -> str:
    """
    Executes a Python code block and returns stdout output.
    Supports math, financial metrics, CAGR, forecasts, etc.
    Always print() your final result.

    Args:
        code: Valid Python code to execute.
        timeout_seconds: Max execution time (default 10s).

    Returns:
        Captured stdout, or an error/traceback string.
    """
    # Single shared env so variable references resolve correctly
    env = {"__builtins__": _SAFE_BUILTINS}

    stdout_capture = io.StringIO()

    # Thread-safe stdout redirect
    try:
        with contextlib.redirect_stdout(stdout_capture):
            # Timeout via SIGALRM (Unix only; skip on Windows)
            if hasattr(signal, "SIGALRM"):
                signal.signal(signal.SIGALRM, _timeout_handler)
                signal.alarm(timeout_seconds)
            try:
                exec(code, env)  # single dict: globals == locals
            finally:
                if hasattr(signal, "SIGALRM"):
                    signal.alarm(0)  # cancel alarm

        output = stdout_capture.getvalue()
        if not output.strip():
            return "Execution completed with no output. Did you forget to print() your result?"
        return output

    except TimeoutError as e:
        return f"Execution timed out after {timeout_seconds}s: {e}"
    except Exception:
        import traceback
        return f"Execution failed:\n{traceback.format_exc()}"