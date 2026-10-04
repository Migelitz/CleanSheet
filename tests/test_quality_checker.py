from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
from _pytest.fixtures import FixtureRequest

from cleansheet.quality.quality_checker import check_quality

"""
Testing configuration: chunk_size is monkeypatched to 5 so the 10-row
fixtures are processed across multiple chunks. Production uses 50_000.

Known behavior: CSV files are processed in chunks, so pandas performs dtype
inference at the chunk level. This can preserve mixed Python types within a
column when type drift occurs between chunks. XLSX/XLS files are currently
loaded as complete worksheets, causing pandas to infer the dtype from the
entire column. Consequently, mixed-type columns may be represented
differently for Excel inputs. This affects baseline_dtypes and unique_values,
but does not affect the core numerical, missingness, sentinel, duplicate,
or statistical quality calculations.
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
def report(request: FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setattr("cleansheet.quality.quality_checker.chunk_size", 5)
    filepath = BASE_DIR / "assets" / "test_files" / request.param
    return check_quality(filepath)


def test_dataset_geometry(report: dict[str, Any]) -> None:
    assert report["rows"] == 10
    assert report["columns"] == 6
    assert report["column_names"] == ["num_a", "num_b", "category", "sentinels", "all_empty", "drift_test"]
    assert report["empty_columns"] == ["all_empty"]


@pytest.mark.parametrize(
    "filename, expected_drifts",
    [
        ("quality_test.csv", {"drift_test": True}),
        ("quality_test.xlsx", {}),
        ("quality_test.xls", {}),
    ],
)
def test_schema_integrity(filename: str, expected_drifts: dict[str, bool], monkeypatch: pytest.MonkeyPatch) -> None:

    monkeypatch.setattr("cleansheet.quality.quality_checker.chunk_size", 5)
    filepath = BASE_DIR / "assets" / "test_files" / filename
    report = check_quality(filepath)

    assert set(report["baseline_dtypes"]) == {
        "num_a",
        "num_b",
        "category",
        "sentinels",
        "all_empty",
        "drift_test",
    }

    assert report["type_drifts"] == expected_drifts


def test_missingness(report: dict[str, Any]) -> None:
    assert report["null_counts"] == {
        "num_a": 0,
        "num_b": 1,
        "category": 0,
        "sentinels": 0,
        "all_empty": 10,
        "drift_test": 0,
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


def test_sentinel_detection(report: dict[str, Any]) -> None:
    assert report["sentinel_counts"] == {
        "num_a": 0,
        "num_b": 0,
        "category": 0,
        "sentinels": 7,
        "all_empty": 0,
        "drift_test": 0,
    }


def test_numeric_health(report: dict[str, Any]) -> None:
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


def test_duplicates(report: dict[str, Any]) -> None:
    assert report["duplicate_counts"] == 1


def test_central_tendency(report: dict[str, Any]) -> None:
    assert report["running_sum"]["num_a"] == 75.0
    assert report["numeric_counts"]["num_a"] == 10
    assert report["global_mean"]["num_a"] == 7.5
    assert report["running_sum"]["num_b"] == 180.0
    assert report["numeric_counts"]["num_b"] == 9
    assert report["global_mean"]["num_b"] == 20.0


def test_dispersion(report: dict[str, Any]) -> None:
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


def test_covariance(report: dict[str, Any]) -> None:
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


def test_categorical_cardinality(report: dict[str, Any]) -> None:
    assert report["unique_values"]["num_a"] == {10, -5, 0, 15, 25, -15, 30, 5}

    assert report["unique_values"]["num_b"] == {20.0, 0.0, -10.0, 30.0, 50.0, 60.0, 10.0}

    assert report["unique_values"]["category"] == {"Alpha", "Beta", "Gamma"}

    assert report["unique_values"]["sentinels"] == {
        "?",
        "missing",
        "DK",
        "#DIV/0!",
        "1970-01-01",
        "valid_text",
        "-",
    }

    assert report["unique_values"]["all_empty"] == set()

    # Values retain their original chunk-level types.
    # Because drift_test changes from int64 to object when "text_drift"
    # appears, earlier chunks contribute integers while later numeric-looking
    # values are parsed as strings. Still the goal is finding unique values
    # Normalize the intentional type difference
    assert {str(value) for value in report["unique_values"]["drift_test"]} == {
        "100",
        "200",
        "300",
        "400",
        "500",
        "600",
        "700",
        "800",
        "text_drift",
    }


def _quality_report(
    frame: pd.DataFrame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    chunk_size: int = 2,
) -> dict[str, Any]:

    monkeypatch.setattr("cleansheet.quality.quality_checker.chunk_size", chunk_size)
    filepath = tmp_path / "quality_regression.csv"
    frame.to_csv(filepath, index=False)
    return check_quality(filepath)


def test_drifted_column_removes_pairwise_statistics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

    frame = pd.DataFrame(
        {
            "drifted": [1, 2, "text", 4],
            "stable": [10, 20, 30, 40],
        }
    )

    report = _quality_report(frame, tmp_path, monkeypatch, chunk_size=2)

    assert report["type_drifts"] == {"drifted": True}
    assert report["sample_covariance"] == {}
    assert report["population_covariance"] == {}
    assert report["pearson_correlation"] == {}


def test_pearson_uses_pairwise_aligned_variance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

    frame = pd.DataFrame(
        {
            "a": [10, 20, 30, np.nan],
            "b": [100, 200, np.nan, 400],
        }
    )

    report = _quality_report(frame, tmp_path, monkeypatch)

    pair = ("a", "b")
    assert report["sample_covariance"][pair] == pytest.approx(500.0)
    assert report["pearson_correlation"][pair] == pytest.approx(1.0)


def test_pearson_is_one_for_complete_linearly_related_pairs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

    frame = pd.DataFrame({"a": [1, 2, 3], "b": [2, 4, 6]})

    report = _quality_report(frame, tmp_path, monkeypatch)

    assert report["pearson_correlation"][("a", "b")] == pytest.approx(1.0)


def test_pearson_is_none_with_fewer_than_two_pairs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

    frame = pd.DataFrame({"a": [1, np.nan], "b": [2, 3]})

    report = _quality_report(frame, tmp_path, monkeypatch)

    pair = ("a", "b")
    assert report["sample_covariance"][pair] is None
    assert report["pearson_correlation"][pair] is None


def test_pearson_is_none_for_zero_variance_pair(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

    frame = pd.DataFrame({"a": [1, 1, 1], "b": [2, 3, 4]})

    report = _quality_report(frame, tmp_path, monkeypatch)

    assert report["pearson_correlation"][("a", "b")] is None
