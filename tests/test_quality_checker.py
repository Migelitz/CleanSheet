from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.cleansheet.quality.quality_checker import check_quality

"""
CONFIGURATION: chunk_size = 5, to allow the check quality to perform chunking (The actual set value is 50_000)

Known behavior: CSV files are processed in chunks, so pandas performs dtype inference at the chunk level. This can preserve mixed Python types within a column when type drift occurs between chunks. XLSX/XLS files are currently loaded as complete worksheets, causing pandas to infer the dtype from the entire column. Consequently, mixed-type columns may be represented differently for Excel inputs. This affects baseline_dtypes and unique_values, but does not affect the core numerical, missingness, sentinel, duplicate, or statistical quality calculations.
"""

# CSV file path for testing
BASE_DIR = Path(__file__).parent.parent

@pytest.fixture(
    params=[
        "quality_test.csv",
        "quality_test.xlsx",
        "quality_test.xls",
    ]
)
def report(request) -> dict:
    filepath = BASE_DIR / "assets" / "test_files" / request.param
    return check_quality(filepath)

def test_dataset_geometry(report) -> None:
    assert report["rows"] == 10
    assert report["columns"] == 6
    assert report["column_names"] == [
        "num_a", 
        "num_b", 
        "category", 
        "sentinels", 
        "all_empty", 
        "drift_test"
    ]
    assert report["empty_columns"] == ["all_empty"]

def test_schema_integrity(report) -> None:
    assert report["baseline_dtypes"] == {
        "num_a": np.dtype("int64"),
        "num_b": np.dtype("float64"),
        "category": pd.StringDtype(na_value=np.nan),
        "sentinels": pd.StringDtype(na_value=np.nan),
        "all_empty": np.dtype("float64"),
        "drift_test": np.dtype("int64"),
    }
    assert report["type_drifts"] == {
        "drift_test": True
    }

def test_missingness(report) -> None:
    assert report["null_counts"] == {
        "num_a": 0, 
        "num_b": 1, 
        "category": 0, 
        "sentinels": 0, 
        "all_empty": 10, 
        "drift_test": 0
    }
    assert report["null_percentage"] == {
        "num_a": 0.0,
        "num_b": 10.0,
        "category": 0.0,
        "sentinels": 0.0,
        "all_empty": 100.0,
        "drift_test": 0.0,
    }
    assert report["non_null_counts"] == {
        "num_a": 10,
        "num_b": 9,
        "category": 10,
        "sentinels": 10,
        "all_empty": 0,
        "drift_test": 10,
    }
    assert report["non_null_percentage"] == {
        "num_a": 100.0,
        "num_b": 90.0,
        "category": 100.0,
        "sentinels": 100.0,
        "all_empty": 0.0,
        "drift_test": 100.0,
    } 

def test_sentinel_detection(report) -> None:
    assert report["sentinel_counts"] == {
        "num_a": 0,
        "num_b": 0,
        "category": 0,
        "sentinels": 7,
        "all_empty": 0,
        "drift_test": 0,
    }

def test_numeric_health(report) -> None:
    assert report["global_min"] == {
        "num_a": -15,
        "num_b": -10.0,
    }
    assert report["global_max"] == {
        "num_a": 30,
        "num_b": 60.0,
    }
    
    assert report["zero_counts"] == {
        "num_a": 2,
        "num_b": 2,
    }
    assert report["negative_counts"] == {
        "num_a": 2,
        "num_b": 1,
    }

def test_duplicates(report) -> None:
    assert report["duplicate_counts"] == 1

def test_central_tendency(report) -> None:
    assert report["running_sum"]["num_a"] == 75.0
    assert report["numeric_counts"]["num_a"] == 10
    assert report["global_mean"]["num_a"] == 7.5
    assert report["running_sum"]["num_b"] == 180.0
    assert report["numeric_counts"]["num_b"] == 9
    assert report["global_mean"]["num_b"] == 20.0

def test_dispersion(report) -> None:
    assert report["population_variance"]["num_a"] == pytest.approx(
        166.25,
        rel=1e-6,
        abs=1e-9,
    )

    assert report["population_std"]["num_a"] == pytest.approx(
        np.sqrt(166.25),
        rel=1e-6,
        abs=1e-9,
    )

    assert report["sample_variance"]["num_a"] == pytest.approx(
        184.7222222222,
        rel=1e-6,
        abs=1e-9,
    )

    assert report["sample_std"]["num_a"] == pytest.approx(
        np.sqrt(184.7222222222),
        rel=1e-6,
        abs=1e-9,
    )

    assert report["population_variance"]["num_b"] == pytest.approx(
        488.88888888889,
        rel=1e-6,
        abs=1e-9,
    )

    assert report["population_std"]["num_b"] == pytest.approx(
        np.sqrt(488.88888888889),
        rel=1e-6,
        abs=1e-9,
    )

    assert report["sample_variance"]["num_b"] == pytest.approx(
        550,
        rel=1e-6,
        abs=1e-9,
    )

    assert report["sample_std"]["num_b"] == pytest.approx(
        np.sqrt(550),
        rel=1e-6,
        abs=1e-9,
    )

def test_covariance(report) -> None:
    assert report["sample_covariance"][("num_a", "num_b")] == pytest.approx(
        268.75,
        rel=1e-6,
        abs=1e-9,
    )

    assert report["population_covariance"][("num_a", "num_b")] == pytest.approx(
        238.8888888889,
        rel=1e-6,
        abs=1e-9,
    )

def test_categorical_cardinality(report) -> None:
    assert report["unique_values"] == {
        "num_a": {10, -5, 0, 15, 25, -15, 30, 5},
        "num_b": {20.0, 0.0, -10.0, 30.0, 50.0, 60.0, 10.0},
        "category": {"Alpha", "Beta", "Gamma"},
        "sentinels": {
            "?",
            "missing",
            "DK",
            "#DIV/0!",
            "1970-01-01",
            "valid_text",
            "-",
        },
        "all_empty": set(),

        # Values retain their original chunk-level types.
        # Because drift_test changes from int64 to object when "text_drift"
        # appears, earlier chunks contribute integers while later numeric-looking
        # values are parsed as strings. Still the goal is finding unique values
        "drift_test": {
            100,
            200,
            300,
            400,
            "500",
            "600",
            "700",
            "800",
            "text_drift",
        },
    }