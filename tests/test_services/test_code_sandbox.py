"""Unit Tests for CodeSandboxService."""
import pytest
from src.services.code_sandbox_service import code_sandbox_service, validate_python_code


def test_validate_python_code_accepts_clean_scientific_code():
    code = """
import pandas as pd
import numpy as np

arr = np.array([1, 2, 3, 4, 5])
print("Mean:", arr.mean())
"""
    err = validate_python_code(code)
    assert err is None


def test_validate_python_code_blocks_dangerous_modules():
    code = """
import os
os.system("ls")
"""
    err = validate_python_code(code)
    assert err is not None
    assert "os" in err


def test_validate_python_code_blocks_subprocess_and_calls():
    code = """
import subprocess
subprocess.run(["echo", "hello"])
"""
    err = validate_python_code(code)
    assert err is not None
    assert "subprocess" in err


@pytest.mark.asyncio
async def test_execute_code_with_dataframe_and_stdout():
    csv_data = "City,AQI,PM25\nHanoi,165,85.2\nSaigon,95,35.0\nDanang,55,14.2"
    code = """
avg_aqi = df['AQI'].mean()
print(f"Average AQI: {avg_aqi:.2f}")
"""
    res = await code_sandbox_service.execute_code_async(code=code, csv_text=csv_data)
    assert res.success is True
    assert "Average AQI: 105.00" in res.stdout
    assert res.execution_time_ms >= 0


@pytest.mark.asyncio
async def test_execute_code_captures_matplotlib_figures():
    csv_data = "Month,Sales\nJan,100\nFeb,150\nMar,200"
    code = """
import matplotlib.pyplot as plt

plt.figure(figsize=(6, 4))
plt.plot(df['Month'], df['Sales'], marker='o')
plt.title("Sales Trend")
"""
    res = await code_sandbox_service.execute_code_async(code=code, csv_text=csv_data)
    assert res.success is True
    assert len(res.figures) >= 1
    assert res.figures[0].startswith("data:image/png;base64,")


@pytest.mark.asyncio
async def test_execute_code_handles_runtime_exceptions_gracefully():
    code = """
x = 10 / 0
"""
    res = await code_sandbox_service.execute_code_async(code=code)
    assert res.success is False
    assert "ZeroDivisionError" in (res.error or "")


def test_smart_repair_python_code_fixes_unexpected_indent():
    from src.services.code_sandbox_service import smart_repair_python_code
    
    # Indented block with leading comment (the exact bug case)
    broken_code = """
# Step 1: Initialize
    import pandas as pd
    import numpy as np
    
    # Step 2: Compute stats
    data = [10, 20, 30]
    res = np.mean(data)
"""
    repaired = smart_repair_python_code(broken_code)
    err = validate_python_code(repaired)
    assert err is None
    assert "import pandas as pd" in repaired


@pytest.mark.asyncio
async def test_execute_code_auto_repairs_indented_blocks():
    # Code with unexpected indentation that previously failed AST parsing
    code_with_indent = """
    # Plotting code with 4 spaces indent
    import matplotlib.pyplot as plt
    plt.figure(figsize=(4, 3))
    plt.plot([1, 2, 3], [4, 5, 6])
"""
    res = await code_sandbox_service.execute_code_async(code=code_with_indent)
    assert res.success is True
    assert len(res.figures) >= 1


@pytest.mark.asyncio
async def test_execute_code_supports_statsmodels():
    pytest.importorskip("statsmodels")
    code = """
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
import numpy as np

series = np.random.normal(0, 1, 100)
result = adfuller(series)
print("ADF p-value:", round(result[1], 4))
"""
    res = await code_sandbox_service.execute_code_async(code=code)
    assert res.success is True
    assert "ADF p-value:" in res.stdout


