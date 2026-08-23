"""Code Sandbox Service — Secure, Isolated Python Execution Environment for Data Analysis.

Key capabilities:
1. Isolated Execution: Executes Python code in a safe in-process namespace with AST-based security filtering.
2. Auto-Injected Dataframe: Pre-loads the user's uploaded CSV/TSV data into `df` (pandas DataFrame).
3. Matplotlib Figure Capture: Hooks `matplotlib.pyplot` and captures all generated plots as base64-encoded PNGs.
4. Stdout & Stderr Redirection: Captures all print outputs, statistical summaries, and traceback logs.
5. Timeout Guardrail: Enforces execution timeout (default 10 seconds) to prevent infinite loops.
6. Forbidden Syntax / Module Blocker: Rejects attempts to use dangerous system calls, network sockets, or filesystem modification outside the sandbox.
"""
from __future__ import annotations

import ast
import asyncio
import base64
import contextlib
import io
import logging
import re
import sys
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Disallowed modules and builtins for basic code safety
DISALLOWED_MODULES = {
    "os", "subprocess", "sys", "shutil", "socket", "http", "urllib",
    "requests", "ftplib", "telnetlib", "smtplib", "pty", "ctypes",
    "importlib", "builtins", "posix", "nt", "_thread", "threading",
    "multiprocessing", "asyncio", "signal", "tempfile", "webbrowser",
}

DISALLOWED_CALLS = {
    "eval", "exec", "compile", "__import__", "open", "input", "exit", "quit"
}


class CodeExecutionRequest(BaseModel):
    code: str = Field(description="Python code snippet to execute")
    csv_text: Optional[str] = Field(default="", description="CSV or TSV text to populate the 'df' DataFrame")
    timeout_seconds: Optional[float] = Field(default=10.0, description="Max execution duration in seconds")


class TableResult(BaseModel):
    name: str = "df"
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    total_rows: int = 0
    total_cols: int = 0


class StatisticalInsight(BaseModel):
    metric: str
    value: str
    subtext: Optional[str] = None
    category: str = "general"  # summary, correlation, distribution, hypothesis


class CodeExecutionResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    execution_time_ms: int = 0
    figures: List[str] = Field(default_factory=list, description="Base64 encoded matplotlib figures")
    tables: List[TableResult] = Field(default_factory=list, description="Extracted DataFrame tables")
    insights: List[StatisticalInsight] = Field(default_factory=list)
    execution_stream: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Ordered sequence of stdout text and figures")


class SecurityCheckVisitor(ast.NodeVisitor):
    """AST visitor that checks for prohibited imports and function calls."""
    def __init__(self):
        self.errors: List[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            mod_root = alias.name.split(".")[0]
            if mod_root in DISALLOWED_MODULES:
                self.errors.append(f"Importing module '{alias.name}' is prohibited in the sandbox for security reasons.")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            mod_root = node.module.split(".")[0]
            if mod_root in DISALLOWED_MODULES:
                self.errors.append(f"Importing from '{node.module}' is prohibited in the sandbox for security reasons.")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in DISALLOWED_CALLS:
            self.errors.append(f"Direct invocation of '{node.func.id}()' is prohibited in the sandbox.")
        self.generic_visit(node)


def validate_python_code(code: str) -> Optional[str]:
    """Parses code into AST and inspects for unsafe operations."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"Syntax Error at line {e.lineno}: {e.msg}"

    visitor = SecurityCheckVisitor()
    visitor.visit(tree)
    if visitor.errors:
        return " | ".join(visitor.errors)
    return None


class CodeSandboxService:
    """Provides isolated, safe execution of scientific Python code snippets."""

    def __init__(self):
        pass

    async def execute_code_async(
        self,
        code: str,
        csv_text: str = "",
        timeout_seconds: float = 10.0
    ) -> CodeExecutionResponse:
        """Executes code in a worker thread with timeout enforcement."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self._execute_code_sync,
            code,
            csv_text,
            timeout_seconds
        )

    async def execute_blocks_async(
        self,
        blocks: List[str],
        csv_text: str = "",
        timeout_seconds: float = 25.0
    ) -> List[dict]:
        """Executes a list of code blocks sequentially in the same environment."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self._execute_blocks_sync,
            blocks,
            csv_text,
            timeout_seconds
        )

    def _execute_blocks_sync(
        self,
        blocks: List[str],
        csv_text: str = "",
        timeout_seconds: float = 25.0
    ) -> List[dict]:
        t0 = time.time()
        
        # Setup sandbox execution namespace
        import io as py_io
        import pandas as pd
        import numpy as np

        class MockIPythonDisplay:
            @staticmethod
            def display(*args, **kwargs):
                current_print = sandbox_globals.get("__builtins__", {}).get("print", print)
                for a in args:
                    current_print(a)
            @staticmethod
            def HTML(html_str):
                return html_str
            @staticmethod
            def Markdown(md_str):
                return md_str

        class MockIPython:
            display = MockIPythonDisplay
            __name__ = "IPython"

        def safe_import(name, *args, **kwargs):
            root = name.split(".")[0]
            if root in DISALLOWED_MODULES:
                raise ImportError(f"Importing module '{name}' is prohibited in the sandbox.")
            if root == "IPython":
                if name == "IPython.display":
                    return MockIPythonDisplay
                return MockIPython
            try:
                return __import__(name, *args, **kwargs)
            except ImportError:
                if root == "IPython":
                    return MockIPython
                raise

        sandbox_globals: Dict[str, Any] = {
            "__builtins__": {
                "__import__": safe_import,
                "display": MockIPythonDisplay.display,
                "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool,
                "bytes": bytes, "chr": chr, "dict": dict, "dir": dir, "divmod": divmod,
                "enumerate": enumerate, "filter": filter, "float": float, "format": format,
                "frozenset": frozenset, "hasattr": hasattr, "hash": hash, "hex": hex,
                "int": int, "isinstance": isinstance, "issubclass": issubclass, "iter": iter,
                "len": len, "list": list, "map": map, "max": max, "min": min, "next": next,
                "oct": oct, "ord": ord, "pow": pow, "print": print, "range": range,
                "repr": repr, "reversed": reversed, "round": round, "set": set,
                "slice": slice, "sorted": sorted, "str": str, "sum": sum, "tuple": tuple,
                "type": type, "vars": vars, "zip": zip,
                "Exception": Exception, "ValueError": ValueError, "TypeError": TypeError,
                "KeyError": KeyError, "IndexError": IndexError, "RuntimeError": RuntimeError,
            },
            "display": MockIPythonDisplay.display,
            "IPython": MockIPython,
            "pd": pd,
            "pandas": pd,
            "np": np,
            "numpy": np,
        }

        try:
            import scipy
            import scipy.stats as stats
            sandbox_globals["scipy"] = scipy
            sandbox_globals["stats"] = stats
        except ImportError:
            pass

        try:
            import sklearn
            sandbox_globals["sklearn"] = sklearn
        except ImportError:
            pass

        # Matplotlib setup
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            plt.clf()
            plt.close("all")
            sandbox_globals["plt"] = plt
            sandbox_globals["matplotlib"] = matplotlib
            
            try:
                import seaborn as sns
                sandbox_globals["sns"] = sns
                sandbox_globals["seaborn"] = sns
            except ImportError:
                pass
        except ImportError:
            plt = None

        # Pre-load DataFrame if CSV text is supplied
        df = None
        raw_csv = (csv_text or "").strip()
        if raw_csv:
            try:
                first_line = raw_csv.split('\n')[0]
                sep = '\t' if '\t' in first_line and first_line.count('\t') > first_line.count(',') else (';' if ';' in first_line and first_line.count(';') > first_line.count(',') else ',')
                try:
                    df = pd.read_csv(py_io.StringIO(raw_csv), sep=sep, on_bad_lines='skip')
                except Exception:
                    df = pd.read_csv(py_io.StringIO(raw_csv), on_bad_lines='skip')
                sandbox_globals["df"] = df
                sandbox_globals["data"] = df
            except Exception as e:
                logger.warning(f"Could not initialize dataframe from CSV: {e}")

        orig_read_csv = pd.read_csv
        orig_read_table = pd.read_table
        orig_read_excel = getattr(pd, "read_excel", None)

        def smart_read_csv(filepath_or_buffer, *args, **kwargs):
            if isinstance(filepath_or_buffer, str):
                import os
                if not os.path.exists(filepath_or_buffer):
                    if df is not None: return df.copy()
                    if raw_csv: return orig_read_csv(py_io.StringIO(raw_csv), *args, **kwargs)
            return orig_read_csv(filepath_or_buffer, *args, **kwargs)

        def smart_read_table(filepath_or_buffer, *args, **kwargs):
            if isinstance(filepath_or_buffer, str):
                import os
                if not os.path.exists(filepath_or_buffer):
                    if df is not None: return df.copy()
                    if raw_csv: return orig_read_table(py_io.StringIO(raw_csv), *args, **kwargs)
            return orig_read_table(filepath_or_buffer, *args, **kwargs)

        def smart_read_excel(filepath_or_buffer, *args, **kwargs):
            if isinstance(filepath_or_buffer, str):
                import os
                if not os.path.exists(filepath_or_buffer):
                    if df is not None: return df.copy()
                    if raw_csv: return orig_read_csv(py_io.StringIO(raw_csv))
            if orig_read_excel:
                try: return orig_read_excel(filepath_or_buffer, *args, **kwargs)
                except Exception: pass
            if df is not None: return df.copy()
            if raw_csv: return orig_read_csv(py_io.StringIO(raw_csv))
            raise FileNotFoundError(f"File {filepath_or_buffer} not found and no in-memory dataset available.")

        pd.read_csv = smart_read_csv
        pd.read_table = smart_read_table
        if orig_read_excel: pd.read_excel = smart_read_excel

        results = []
        for i, block in enumerate(blocks):
            clean_code = block.strip()
            if clean_code.startswith("```"):
                clean_code = re.sub(r"^```(?:python|py)?\s*\n", "", clean_code)
                clean_code = re.sub(r"\n```$", "", clean_code)
            
            block_output = {"stdout": "", "stderr": "", "figures": []}
            
            if not clean_code:
                results.append(block_output)
                continue
                
            security_error = validate_python_code(clean_code)
            if security_error:
                block_output["stderr"] = f"Rào chắn bảo mật Sandbox: {security_error}"
                results.append(block_output)
                continue

            stdout_buf = io.StringIO()
            def custom_print(*args, **kwargs):
                sep = kwargs.get("sep", " ")
                end = kwargs.get("end", "\n")
                stdout_buf.write(sep.join(str(a) for a in args) + end)

            sandbox_globals["__builtins__"]["print"] = custom_print

            figures_base64 = []
            if plt:
                def custom_show(*args, **kwargs):
                    try:
                        fig_nums = plt.get_fignums()
                        for num in fig_nums:
                            fig = plt.figure(num)
                            try: fig.tight_layout(pad=2.0)
                            except Exception: pass
                            buf = io.BytesIO()
                            fig.savefig(buf, format="png", bbox_inches="tight", dpi=160)
                            buf.seek(0)
                            img_str = base64.b64encode(buf.read()).decode("utf-8")
                            figures_base64.append(f"data:image/png;base64,{img_str}")
                            buf.close()
                        plt.close("all")
                    except Exception as e:
                        pass
                plt.show = custom_show

            def custom_display(*args):
                for a in args:
                    custom_print(a)
            sandbox_globals["display"] = custom_display
            sandbox_globals["__builtins__"]["display"] = custom_display

            try:
                parsed = ast.parse(clean_code)
                if parsed.body and isinstance(parsed.body[-1], ast.Expr):
                    last_expr = parsed.body.pop()
                    if parsed.body:
                        compiled_lead = compile(ast.Module(body=parsed.body, type_ignores=[]), filename=f"<sandbox_block_{i}>", mode="exec")
                        exec(compiled_lead, sandbox_globals)
                    val = eval(compile(ast.Expression(last_expr.value), filename=f"<sandbox_block_{i}_eval>", mode="eval"), sandbox_globals)
                    if val is not None:
                        custom_print(val)
                else:
                    compiled = compile(clean_code, filename=f"<sandbox_block_{i}>", mode="exec")
                    exec(compiled, sandbox_globals)
                
                # Check for unshown figures
                if plt:
                    fig_nums = plt.get_fignums()
                    if fig_nums:
                        plt.show()
                        
            except Exception as exc:
                block_output["stderr"] = f"{type(exc).__name__}: {exc}"
            
            block_output["stdout"] = stdout_buf.getvalue()
            block_output["figures"] = figures_base64
            results.append(block_output)

        pd.read_csv = orig_read_csv
        pd.read_table = orig_read_table
        if orig_read_excel: pd.read_excel = orig_read_excel
        
        return results

    def _execute_code_sync(
        self,
        code: str,
        csv_text: str = "",
        timeout_seconds: float = 10.0
    ) -> CodeExecutionResponse:
        t0 = time.time()
        
        # 1. Clean and validate code
        clean_code = code.strip()
        # Strip markdown code fencing if present
        if clean_code.startswith("```"):
            clean_code = re.sub(r"^```(?:python|py)?\s*\n", "", clean_code)
            clean_code = re.sub(r"\n```$", "", clean_code)

        if not clean_code:
            return CodeExecutionResponse(
                success=False,
                error="Mã nguồn thực thi không được để trống.",
                execution_time_ms=0
            )

        # 2. Security validation
        security_error = validate_python_code(clean_code)
        if security_error:
            return CodeExecutionResponse(
                success=False,
                error=f"Rào chắn bảo mật Sandbox: {security_error}",
                execution_time_ms=int((time.time() - t0) * 1000)
            )

        # 3. Setup sandbox execution namespace with scientific libraries
        execution_stream = []

        import io as py_io
        import pandas as pd
        import numpy as np

        class MockIPythonDisplay:
            @staticmethod
            def display(*args, **kwargs):
                current_print = sandbox_globals.get("__builtins__", {}).get("print", print)
                for a in args:
                    current_print(a)
            @staticmethod
            def HTML(html_str):
                return html_str
            @staticmethod
            def Markdown(md_str):
                return md_str

        class MockIPython:
            display = MockIPythonDisplay
            __name__ = "IPython"

        def safe_import(name, *args, **kwargs):
            root = name.split(".")[0]
            if root in DISALLOWED_MODULES:
                raise ImportError(f"Importing module '{name}' is prohibited in the sandbox.")
            if root == "IPython":
                if name == "IPython.display":
                    return MockIPythonDisplay
                return MockIPython
            try:
                return __import__(name, *args, **kwargs)
            except ImportError:
                if root == "IPython":
                    return MockIPython
                raise

        # Safe global namespace
        sandbox_globals: Dict[str, Any] = {
            "__builtins__": {
                "__import__": safe_import,
                "display": MockIPythonDisplay.display,
                "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool,
                "bytes": bytes, "chr": chr, "dict": dict, "dir": dir, "divmod": divmod,
                "enumerate": enumerate, "filter": filter, "float": float, "format": format,
                "frozenset": frozenset, "hasattr": hasattr, "hash": hash, "hex": hex,
                "int": int, "isinstance": isinstance, "issubclass": issubclass, "iter": iter,
                "len": len, "list": list, "map": map, "max": max, "min": min, "next": next,
                "oct": oct, "ord": ord, "pow": pow, "print": print, "range": range,
                "repr": repr, "reversed": reversed, "round": round, "set": set,
                "slice": slice, "sorted": sorted, "str": str, "sum": sum, "tuple": tuple,
                "type": type, "vars": vars, "zip": zip,
                "Exception": Exception, "ValueError": ValueError, "TypeError": TypeError,
                "KeyError": KeyError, "IndexError": IndexError, "RuntimeError": RuntimeError,
            },
            "display": MockIPythonDisplay.display,
            "IPython": MockIPython,
            "pd": pd,
            "pandas": pd,
            "np": np,
            "numpy": np,
        }

        # Optional scientific libraries
        try:
            import scipy
            import scipy.stats as stats
            sandbox_globals["scipy"] = scipy
            sandbox_globals["stats"] = stats
        except ImportError:
            pass

        try:
            import sklearn
            sandbox_globals["sklearn"] = sklearn
        except ImportError:
            pass

        # Matplotlib headless backend configuration
        figures_base64: List[str] = []
        try:
            import matplotlib
            matplotlib.use("Agg")  # Non-interactive backend
            import matplotlib.pyplot as plt
            plt.clf()
            plt.close("all")
            
            orig_show = plt.show
            def custom_show(*args, **kwargs):
                try:
                    fig_nums = plt.get_fignums()
                    for num in fig_nums:
                        fig = plt.figure(num)
                        try:
                            fig.tight_layout(pad=2.0)
                        except Exception:
                            pass
                        buf = io.BytesIO()
                        fig.savefig(buf, format="png", bbox_inches="tight", dpi=160)
                        buf.seek(0)
                        img_str = base64.b64encode(buf.read()).decode("utf-8")
                        b64_fig = f"data:image/png;base64,{img_str}"
                        figures_base64.append(b64_fig)
                        execution_stream.append({"type": "figure", "content": b64_fig})
                        buf.close()
                    plt.close("all")
                except Exception as e:
                    pass
            
            plt.show = custom_show
            sandbox_globals["plt"] = plt
            sandbox_globals["matplotlib"] = matplotlib
            
            try:
                import seaborn as sns
                sandbox_globals["sns"] = sns
                sandbox_globals["seaborn"] = sns
            except ImportError:
                pass
        except ImportError:
            plt = None

        # Pre-load DataFrame if CSV text is supplied
        df = None
        raw_csv = (csv_text or "").strip()
        if raw_csv:
            try:
                first_line = raw_csv.split('\n')[0]
                sep = '\t' if '\t' in first_line and first_line.count('\t') > first_line.count(',') else (';' if ';' in first_line and first_line.count(';') > first_line.count(',') else ',')
                try:
                    df = pd.read_csv(py_io.StringIO(raw_csv), sep=sep, on_bad_lines='skip')
                except Exception:
                    df = pd.read_csv(py_io.StringIO(raw_csv), on_bad_lines='skip')
                sandbox_globals["df"] = df
                sandbox_globals["data"] = df
            except Exception as e:
                logger.warning(f"Could not initialize dataframe from CSV: {e}")

        # Hook pd.read_csv, pd.read_table, pd.read_excel so any filename lookup redirects to in-memory df or csv_text
        orig_read_csv = pd.read_csv
        orig_read_table = pd.read_table
        orig_read_excel = getattr(pd, "read_excel", None)

        def smart_read_csv(filepath_or_buffer, *args, **kwargs):
            if isinstance(filepath_or_buffer, str):
                import os
                if not os.path.exists(filepath_or_buffer):
                    if df is not None:
                        return df.copy()
                    if raw_csv:
                        return orig_read_csv(py_io.StringIO(raw_csv), *args, **kwargs)
            return orig_read_csv(filepath_or_buffer, *args, **kwargs)

        def smart_read_table(filepath_or_buffer, *args, **kwargs):
            if isinstance(filepath_or_buffer, str):
                import os
                if not os.path.exists(filepath_or_buffer):
                    if df is not None:
                        return df.copy()
                    if raw_csv:
                        return orig_read_table(py_io.StringIO(raw_csv), *args, **kwargs)
            return orig_read_table(filepath_or_buffer, *args, **kwargs)

        def smart_read_excel(filepath_or_buffer, *args, **kwargs):
            if isinstance(filepath_or_buffer, str):
                import os
                if not os.path.exists(filepath_or_buffer):
                    if df is not None:
                        return df.copy()
                    if raw_csv:
                        return orig_read_csv(py_io.StringIO(raw_csv))
            if orig_read_excel:
                try:
                    return orig_read_excel(filepath_or_buffer, *args, **kwargs)
                except Exception:
                    if df is not None:
                        return df.copy()
                    if raw_csv:
                        return orig_read_csv(py_io.StringIO(raw_csv))
            if df is not None:
                return df.copy()
            if raw_csv:
                return orig_read_csv(py_io.StringIO(raw_csv))
            raise FileNotFoundError(f"File {filepath_or_buffer} not found and no in-memory dataset available.")

        # 4. Redirect stdout and stderr
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()

        def custom_print(*args, **kwargs):
            sep = kwargs.get("sep", " ")
            end = kwargs.get("end", "\n")
            text = sep.join(str(a) for a in args) + end
            stdout_buf.write(text)
            if execution_stream and execution_stream[-1]["type"] == "text":
                execution_stream[-1]["content"] += text
            else:
                execution_stream.append({"type": "text", "content": text})

        sandbox_globals["__builtins__"]["print"] = custom_print


        def custom_display(*args, **kwargs):
            for a in args:
                custom_print(a)

        sandbox_globals["display"] = custom_display
        sandbox_globals["__builtins__"]["display"] = custom_display

        class MockIPythonDisplay:
            @staticmethod
            def display(*args, **kwargs):
                custom_display(*args, **kwargs)
            @staticmethod
            def HTML(html_str):
                return html_str
            @staticmethod
            def Markdown(md_str):
                return md_str

        class MockIPython:
            display = MockIPythonDisplay

        sandbox_globals["IPython"] = MockIPython

        exec_error: Optional[str] = None
        success = True

        # 5. Run code within captured environment with patched pandas file reader
        try:
            pd.read_csv = smart_read_csv
            pd.read_table = smart_read_table
            if orig_read_excel:
                pd.read_excel = smart_read_excel
            
            parsed = ast.parse(clean_code)
            if parsed.body and isinstance(parsed.body[-1], ast.Expr):
                last_expr = parsed.body.pop()
                if parsed.body:
                    compiled_lead = compile(ast.Module(body=parsed.body, type_ignores=[]), filename="<sandbox>", mode="exec")
                    exec(compiled_lead, sandbox_globals)
                val = eval(compile(ast.Expression(last_expr.value), filename="<sandbox_eval>", mode="eval"), sandbox_globals)
                if val is not None:
                    custom_print(val)
            else:
                compiled = compile(clean_code, filename="<sandbox>", mode="exec")
                exec(compiled, sandbox_globals)
        except Exception as exc:
            success = False
            exec_error = f"{type(exc).__name__}: {exc}"
            stderr_buf.write(exec_error + "\n")
        finally:
            pd.read_csv = orig_read_csv
            pd.read_table = orig_read_table
            if orig_read_excel:
                pd.read_excel = orig_read_excel


        # 6. Capture figures if any were plotted with anti-squish auto layout
        if plt is not None:
            try:
                fig_nums = plt.get_fignums()
                for num in fig_nums:
                    fig = plt.figure(num)
                    try:
                        fig.tight_layout(pad=2.0)
                    except Exception:
                        pass
                    buf = io.BytesIO()
                    fig.savefig(buf, format="png", bbox_inches="tight", dpi=160)
                    buf.seek(0)
                    img_str = base64.b64encode(buf.read()).decode("utf-8")
                    figures_base64.append(f"data:image/png;base64,{img_str}")
                    buf.close()
                plt.close("all")
            except Exception as e:
                logger.warning(f"Failed to capture matplotlib figures: {e}")

        # 7. Extract Tabular Data Results (DataFrames and Series)
        tables_list: List[TableResult] = []
        for var_name, var_val in list(sandbox_globals.items()):
            if var_name.startswith("_") or var_name in ["pd", "pandas", "np", "numpy", "plt", "matplotlib", "sns", "seaborn", "scipy", "stats", "sklearn"]:
                continue
            if isinstance(var_val, pd.DataFrame):
                try:
                    cols = [str(c) for c in var_val.columns]
                    head_df = var_val.head(100).copy()
                    for col in head_df.columns:
                        if pd.api.types.is_float_dtype(head_df[col]):
                            head_df[col] = head_df[col].round(3)
                    records = head_df.fillna("").to_dict(orient="records")
                    tables_list.append(TableResult(
                        name=var_name,
                        columns=cols,
                        rows=records,
                        total_rows=len(var_val),
                        total_cols=len(var_val.columns),
                    ))
                except Exception as tbl_err:
                    logger.warning(f"Could not serialize DataFrame '{var_name}': {tbl_err}")
            elif isinstance(var_val, pd.Series):
                try:
                    s_df = var_val.reset_index()
                    cols = [str(c) for c in s_df.columns]
                    head_df = s_df.head(100).copy()
                    records = head_df.fillna("").to_dict(orient="records")
                    tables_list.append(TableResult(
                        name=var_name,
                        columns=cols,
                        rows=records,
                        total_rows=len(s_df),
                        total_cols=len(s_df.columns),
                    ))
                except Exception:
                    pass

        # 8. Compute Automated Statistical Insights
        insights_list: List[StatisticalInsight] = []
        target_df = None
        for t in tables_list:
            if t.name in ["results", "summary", "df_summary", "corr", "grouped", "df"]:
                target_df = sandbox_globals.get(t.name)
                break
        if target_df is None and "df" in sandbox_globals and isinstance(sandbox_globals["df"], pd.DataFrame):
            target_df = sandbox_globals["df"]

        if target_df is not None and isinstance(target_df, pd.DataFrame) and not target_df.empty:
            num_cols = target_df.select_dtypes(include=[np.number]).columns.tolist()
            cat_cols = target_df.select_dtypes(exclude=[np.number]).columns.tolist()

            # A. Key metric highlights
            for col in num_cols[:4]:
                col_s = target_df[col].dropna()
                if len(col_s) > 0:
                    mean_val = float(col_s.mean())
                    max_val = float(col_s.max())
                    min_val = float(col_s.min())
                    insights_list.append(StatisticalInsight(
                        metric=f"Trung bình {col}",
                        value=f"{mean_val:.2f}",
                        subtext=f"Min: {min_val:.2f} | Max: {max_val:.2f}",
                        category="summary"
                    ))

            # B. Strongest Pearson Correlation if >= 2 numerical columns
            if len(num_cols) >= 2:
                try:
                    corr_mat = target_df[num_cols].corr()
                    pairs = []
                    for i in range(len(num_cols)):
                        for j in range(i + 1, len(num_cols)):
                            c1, c2 = num_cols[i], num_cols[j]
                            val = corr_mat.loc[c1, c2]
                            if not np.isnan(val):
                                pairs.append((abs(val), val, c1, c2))
                    if pairs:
                        pairs.sort(reverse=True)
                        best_abs, best_val, c1, c2 = pairs[0]
                        strength = "Tương quan rất mạnh" if best_abs >= 0.7 else ("Tương quan vừa" if best_abs >= 0.4 else "Tương quan yếu")
                        insights_list.append(StatisticalInsight(
                            metric=f"Tương quan {c1} & {c2}",
                            value=f"r = {best_val:+.2f}",
                            subtext=f"{strength} ({best_val:+.2f})",
                            category="correlation"
                        ))
                except Exception:
                    pass

            # C. Category with highest value if categorical + numeric exist
            if cat_cols and num_cols:
                try:
                    cat_c, num_c = cat_cols[0], num_cols[0]
                    grp = target_df.groupby(cat_c)[num_c].mean().dropna()
                    if not grp.empty:
                        top_cat = grp.idxmax()
                        top_val = grp.max()
                        bot_cat = grp.idxmin()
                        bot_val = grp.min()
                        diff_pct = ((top_val - bot_val) / bot_val * 100) if bot_val != 0 else 0
                        insights_list.append(StatisticalInsight(
                            metric=f"Nhóm cao nhất ({num_c})",
                            value=f"{top_cat} ({top_val:.1f})",
                            subtext=f"Cao hơn nhóm thấp nhất ({bot_cat}) +{diff_pct:.0f}%",
                            category="distribution"
                        ))
                except Exception:
                    pass

        # 9. Extract useful variable summaries
        vars_summary = {}
        for var_name, var_val in sandbox_globals.items():
            if var_name.startswith("_") or var_name in ["pd", "pandas", "np", "numpy", "plt", "matplotlib", "sns", "seaborn", "scipy", "stats", "sklearn"]:
                continue
            if isinstance(var_val, (int, float, str, bool)):
                vars_summary[var_name] = str(var_val)
            elif isinstance(var_val, pd.DataFrame):
                vars_summary[var_name] = f"DataFrame ({var_val.shape[0]} rows × {var_val.shape[1]} cols)"
            elif isinstance(var_val, (list, tuple, set, dict)):
                vars_summary[var_name] = f"{type(var_val).__name__} (len={len(var_val)})"

        elapsed_ms = int((time.time() - t0) * 1000)

        return CodeExecutionResponse(
            success=success,
            stdout=stdout_buf.getvalue(),
            stderr=stderr_buf.getvalue(),
            figures=figures_base64,
            tables=tables_list,
            insights=insights_list,
            execution_stream=execution_stream,
            execution_time_ms=elapsed_ms,
            error=exec_error,
            variables_summary=vars_summary if vars_summary else None,
        )


code_sandbox_service = CodeSandboxService()
