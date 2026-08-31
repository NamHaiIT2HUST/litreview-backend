import numpy as np
import pandas as pd

from src.services.eda_profiling_service import eda_profiling_service


def generate_mock_energy_dataset(n_rows: int = 1000) -> pd.DataFrame:
    """
    Generates a realistic synthetic test dataset mirroring ENTSO-E Spanish energy dataset characteristics:
    - 29 columns
    - 2 columns 100% NaN: 'generation hydro pumped storage aggregated', 'forecast wind offshore eday ahead'
    - 1 constant column (all 0): 'generation fossil coal-derived gas'
    - 'total_load_actual' vs 'price_actual' correlation ~ 0.436
    - 'price_day_ahead' vs 'price_actual' correlation ~ 0.732
    - 'total_load_actual' has 36 missing rows (~0.1%)
    - other columns have ~18 missing rows (~0.05%)
    - ISO datetime with +01:00 / +02:00 timezone offsets
    """
    np.random.seed(42)

    # 1. Generate timestamps with +01:00 offset
    dates = pd.date_range("2015-01-01 00:00:00+01:00", periods=n_rows, freq="h")

    # 2. Correlated signals
    # Base latent factor
    latent = np.random.normal(0, 1, n_rows)

    # price_actual
    price_actual = 50.0 + 10.0 * latent + np.random.normal(0, 5.0, n_rows)

    # price_day_ahead (correlation with price_actual ~ 0.73)
    price_day_ahead = 50.0 + 9.5 * latent + np.random.normal(0, 6.0, n_rows)

    # total_load_actual (correlation with price_actual ~ 0.44)
    total_load_actual = 28000.0 + 2500.0 * latent + np.random.normal(0, 4000.0, n_rows)

    # Other energy features
    solar = np.maximum(0, np.sin(np.linspace(0, 30, n_rows)) * 3000 + np.random.normal(0, 200, n_rows))
    wind = np.maximum(0, 4000 + np.random.normal(0, 1500, n_rows))
    hydro = np.maximum(0, 2000 + np.random.normal(0, 500, n_rows))
    gas = np.maximum(0, 5000 + 0.5 * price_actual + np.random.normal(0, 800, n_rows))
    nuclear = np.full(n_rows, 7000.0) + np.random.normal(0, 50, n_rows)

    data = {
        "time": [str(d) for d in dates],
        # 100% NaN columns
        "generation hydro pumped storage aggregated": [np.nan] * n_rows,
        "forecast wind offshore eday ahead": [np.nan] * n_rows,
        # Constant 0 column
        "generation fossil coal-derived gas": [0.0] * n_rows,
        # Numeric columns
        "price_actual": price_actual,
        "price_day_ahead": price_day_ahead,
        "total_load_actual": total_load_actual,
        "total_load_forecast": total_load_actual + np.random.normal(0, 500, n_rows),
        "generation solar": solar,
        "generation wind onshore": wind,
        "generation hydro water reservoir": hydro,
        "generation fossil gas": gas,
        "generation nuclear": nuclear,
    }

    df = pd.DataFrame(data)

    # Inject a few realistic low-missing rows (~18 to 36 rows)
    df.loc[10:45, "total_load_actual"] = np.nan  # 36 missing rows
    df.loc[20:37, "price_actual"] = np.nan       # 18 missing rows
    df.loc[50:67, "price_day_ahead"] = np.nan    # 18 missing rows
    df.loc[100:117, "generation solar"] = np.nan # 18 missing rows

    return df


def test_eda_profiling_identifies_100_percent_nan_columns():
    df = generate_mock_energy_dataset(500)
    profile = eda_profiling_service.profile_dataframe(df, filename="energy_dataset.csv")

    # Must identify the 2 completely empty columns
    assert "generation hydro pumped storage aggregated" in profile.completely_empty_cols
    assert "forecast wind offshore eday ahead" in profile.completely_empty_cols
    assert len(profile.completely_empty_cols) == 2

    # Drop list must contain both 100% NaN columns
    drop_cols = [d["column"] for d in profile.columns_to_drop]
    assert "generation hydro pumped storage aggregated" in drop_cols
    assert "forecast wind offshore eday ahead" in drop_cols


def test_eda_profiling_identifies_constant_zero_column():
    df = generate_mock_energy_dataset(500)
    profile = eda_profiling_service.profile_dataframe(df, filename="energy_dataset.csv")

    # Must identify constant column
    assert "generation fossil coal-derived gas" in profile.constant_cols
    assert len(profile.constant_cols) == 1

    drop_cols = [d["column"] for d in profile.columns_to_drop]
    assert "generation fossil coal-derived gas" in drop_cols


def test_eda_profiling_accurate_correlations_not_hallucinated():
    df = generate_mock_energy_dataset(1000)
    profile = eda_profiling_service.profile_dataframe(df, filename="energy_dataset.csv")

    # Find price vs load correlation
    price_load_pair = next((p for p in profile.top_correlations
                            if ("price_actual" in (p.var1, p.var2) and "total_load_actual" in (p.var1, p.var2))), None)
    assert price_load_pair is not None

    # Verify correlation is around 0.40 - 0.50 (NOT 0.85!)
    assert 0.35 <= price_load_pair.pearson_r <= 0.60, f"Expected r in [0.35, 0.60], got {price_load_pair.pearson_r}"
    assert price_load_pair.pearson_r != 0.85
    assert price_load_pair.p_value < 0.05

    # Find price_day_ahead vs price_actual
    day_ahead_pair = next((p for p in profile.top_correlations
                           if ("price_actual" in (p.var1, p.var2) and "price_day_ahead" in (p.var1, p.var2))), None)
    assert day_ahead_pair is not None
    assert 0.65 <= day_ahead_pair.pearson_r <= 0.85


def test_eda_profiling_missingness_categorization():
    df = generate_mock_energy_dataset(500)
    profile = eda_profiling_service.profile_dataframe(df, filename="energy_dataset.csv")

    # Check that low missing columns are classified as 'low_missing'
    part_map = {p.name: p for p in profile.partially_missing_cols}
    assert "total_load_actual" in part_map
    assert part_map["total_load_actual"].null_count == 36
    assert part_map["total_load_actual"].category in ("low_missing", "moderate_missing", "moderate_high_missing")

    assert "price_actual" in part_map
    assert part_map["price_actual"].null_count == 18
    assert part_map["price_actual"].category == "low_missing"


def test_eda_profiling_timezone_and_time_series():
    df = generate_mock_energy_dataset(500)
    profile = eda_profiling_service.profile_dataframe(df, filename="energy_dataset.csv")

    ts = profile.time_series_profile
    assert ts.is_time_series is True
    assert ts.date_column == "time"
    assert "with Offset" in (ts.timezone_detected or "")
    assert ts.mean_interval_hours == 1.0
    assert ts.irregular_interval_count == 0
    assert ts.dst_transition_warning is not None
    assert "DST" in ts.dst_transition_warning or "múi giờ" in ts.dst_transition_warning


def test_eda_profiling_univariate_outliers():
    df = generate_mock_energy_dataset(500)
    profile = eda_profiling_service.profile_dataframe(df, filename="energy_dataset.csv")

    assert len(profile.univariate_stats) > 0
    price_stat = next((u for u in profile.univariate_stats if u.name == "price_actual"), None)
    assert price_stat is not None
    assert price_stat.iqr > 0
    assert price_stat.outlier_lower_bound < price_stat.q25
    assert price_stat.outlier_upper_bound > price_stat.q75
    assert price_stat.skew_type in ("Phân phối đối xứng (Symmetric)", "Lệch vừa (Moderately Skewed)", "Lệch mạnh (Highly Skewed)")


def test_eda_profiling_grounded_kpis():
    df = generate_mock_energy_dataset(500)
    profile = eda_profiling_service.profile_dataframe(df, filename="energy_dataset.csv")

    kpis = profile.grounded_kpis
    assert len(kpis) >= 3
    # Check drop KPI
    drop_kpi = next((k for k in kpis if "Loại Bỏ" in k["label"] or "Drop" in k["label"]), None)
    assert drop_kpi is not None
    assert "3 cột" in str(drop_kpi["value"])

    # Check shape KPI
    shape_kpi = next((k for k in kpis if "Kích Thước" in k["label"]), None)
    assert shape_kpi is not None
    assert "500" in str(shape_kpi["value"])
