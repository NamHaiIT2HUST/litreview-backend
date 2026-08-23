import pytest
from tests.test_services.test_eda_profiling_service import generate_mock_energy_dataset


@pytest.mark.asyncio
async def test_workspace_analyze_data_with_energy_csv(client):
    df = generate_mock_energy_dataset(300)
    csv_text = df.to_csv(index=False)
    
    payload = {
        "question": "Thực hiện phân tích EDA toàn diện trên tập dữ liệu năng lượng này.",
        "csv_text": csv_text,
        "filename": "energy_dataset.csv"
    }
    
    response = await client.post("/api/v1/workspace/analyze-data", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Assert answer exists
    assert "answer" in data
    assert len(data["answer"]) > 50
    
    # Assert dataset_profile has verified drop lists and missing info
    profile = data.get("dataset_profile")
    assert profile is not None
    assert profile["row_count"] == 300
    assert len(profile["completely_empty_cols"]) == 2
    assert "generation hydro pumped storage aggregated" in profile["completely_empty_cols"]
    assert "forecast wind offshore eday ahead" in profile["completely_empty_cols"]
    assert "generation fossil coal-derived gas" in profile["constant_cols"]
    
    # Assert KPIs are grounded and non-empty
    kpis = data.get("kpis")
    assert kpis is not None
    assert len(kpis) >= 2
    
    # Verify no KPI claims 0.85 for price vs load
    for kpi in kpis:
        val_str = str(kpi.get("value", ""))
        label_str = str(kpi.get("label", ""))
        if "Tương Quan" in label_str and "Load" in label_str and "Price" in label_str:
            assert "0.85" not in val_str
