import sys, os
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
from src.services.code_sandbox_service import code_sandbox_service, validate_python_code

async def main():
    print("--- 1. Testing Validation ---")
    err1 = validate_python_code("import pandas as pd\nprint(df.head())")
    print("Clean code error (should be None):", err1)
    assert err1 is None

    err2 = validate_python_code("import os\nos.system('ls')")
    print("Unsafe code error (should be caught):", err2)
    assert err2 is not None

    print("\n--- 2. Testing Execution with DataFrame ---")
    csv_text = "City,AQI,Temp\nHanoi,150,28\nSaigon,90,32\nDanang,60,30"
    code = """
import numpy as np
avg_aqi = df['AQI'].mean()
print(f"Mean AQI: {avg_aqi:.1f}")
"""
    res = await code_sandbox_service.execute_code_async(code=code, csv_text=csv_text)
    print("Success:", res.success)
    print("Stdout:", res.stdout.strip())
    print("Error:", res.error)
    print("Stderr:", res.stderr)
    print("Execution time:", res.execution_time_ms, "ms")
    assert res.success is True
    assert "Mean AQI: 100.0" in res.stdout

    print("\n--- 3. Testing Matplotlib & Seaborn Figure Capture ---")
    plot_code = """
import matplotlib.pyplot as plt
import seaborn as sns

plt.figure(figsize=(6, 4))
sns.barplot(data=df, x='City', y='AQI', hue='City', palette='viridis', legend=False)
plt.title('AQI by City with Seaborn')
"""
    res_plot = await code_sandbox_service.execute_code_async(code=plot_code, csv_text=csv_text)
    print("Plot success:", res_plot.success)
    print("Plot error:", res_plot.error)
    print("Plot stderr:", res_plot.stderr)
    print("Figures count:", len(res_plot.figures))
    assert res_plot.success is True
    assert len(res_plot.figures) >= 1
    print("\n--- 4. Testing pd.read_csv('air_quality_seasonal.csv') Lookup ---")
    file_code = """
import pandas as pd
data = pd.read_csv('air_quality_seasonal.csv')
print("Loaded rows:", len(data))
print("Columns:", list(data.columns))
"""
    res_file = await code_sandbox_service.execute_code_async(code=file_code, csv_text=csv_text)
    print("File read success:", res_file.success)
    print("File read stdout:", res_file.stdout.strip())
    print("File read error:", res_file.error)
    assert res_file.success is True
    assert "Loaded rows: 3" in res_file.stdout

    print("\n--- 5. Testing Tabular Results & Statistical Insights Extraction ---")
    eda_code = """
summary = df.describe().reset_index()
grouped = df.groupby('City')['AQI'].mean().reset_index()
"""
    res_eda = await code_sandbox_service.execute_code_async(code=eda_code, csv_text=csv_text)
    print("EDA success:", res_eda.success)
    print("Tables count:", len(res_eda.tables))
    print("Table names:", [t.name for t in res_eda.tables])
    print("Insights count:", len(res_eda.insights))
    print("Insights metrics:", [i.metric for i in res_eda.insights])
    assert res_eda.success is True
    assert len(res_eda.tables) >= 1
    assert len(res_eda.insights) >= 1

    print("\n✅ ALL CODE SANDBOX VERIFICATION TESTS (TABLES + INSIGHTS + SEABORN + AUTO-LAYOUT) PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())
