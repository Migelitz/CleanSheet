import math
from pathlib import Path

import pandas as pd
import pytest

from cleansheet.cleaner.tab_cleaner import clean_dataframe
from cleaner_benchmark import run_benchmark


def test_trim_text_and_strip_characters() -> None:
    source = pd.DataFrame({"name": ["  Alice $ ", " Bob %"]})

    result = clean_dataframe(
        source,
        trim_text=True,
        fill_missing="Keep Missing",
        strip_chars="$,%",
        column_transformations={},
    )

    assert result["name"].tolist() == ["Alice", "Bob"]


@pytest.mark.parametrize(
    ("transformation", "values", "expected"),
    [
        ("lowercase", [" Alice ", "BOB"], [" alice ", "bob"]),
        ("UPPERCASE", [" Alice ", "bob"], [" ALICE ", "BOB"]),
        ("Title Case", ["alice smith", "BOB JONES"], ["Alice Smith", "Bob Jones"]),
        ("Numbers Only", ["ID-12", "(555) 123-4567"], ["12", "5551234567"]),
        ("Clean Currency", ["$1,234.50", "EUR 20"], [1234.50, 20.0]),
        ("Extract Email", ["Contact a@example.com", "invalid"], ["a@example.com", float("nan")]),
        ("Extract URL", ["See https://example.com.", "www.example.org"], ["https://example.com.", "www.example.org"]),
        ("Anonymize Email", ["john.doe@gmail.com"], ["j*******@gmail.com"]),
        ("Anonymize Numbers (Keep Last 4)", ["123456789"], ["*****6789"]),
        ("Date (YYYY-MM-DD)", ["January 2, 2024", "not a date"], ["2024-01-02", float("nan")]),
    ],
)
def test_column_transformations(transformation: str, values: list[str], expected: list[object]) -> None:
    result = clean_dataframe(
        pd.DataFrame({"value": values}),
        trim_text=False,
        fill_missing="Keep Missing",
        strip_chars="",
        column_transformations={"value": transformation},
    )

    actual = result["value"].tolist()
    for actual_value, expected_value in zip(actual, expected):
        if isinstance(expected_value, float) and math.isnan(expected_value):
            assert pd.isna(actual_value)
        else:
            assert actual_value == expected_value


def test_split_human_names_adds_first_and_last_columns() -> None:
    result = clean_dataframe(
        pd.DataFrame({"full_name": ["Dr. John W. Doe Jr.", "Jane Doe"]}),
        trim_text=False,
        fill_missing="Keep Missing",
        strip_chars="",
        column_transformations={"full_name": "Split Human Names"},
    )

    assert result.columns.tolist() == ["full_name", "full_name - First", "full_name - Last"]
    assert result["full_name - First"].tolist() == ["John", "Jane"]
    assert result["full_name - Last"].tolist() == ["Doe", "Doe"]


def test_split_human_names_preserves_missing_values_as_empty_parts() -> None:
    result = clean_dataframe(
        pd.DataFrame({"full_name": [None]}),
        trim_text=False,
        fill_missing="Keep Missing",
        strip_chars="",
        column_transformations={"full_name": "Split Human Names"},
    )

    assert result[["full_name - First", "full_name - Last"]].iloc[0].tolist() == ["", ""]


@pytest.mark.parametrize("fill_missing", ["Drop Rows", "Fill 'N/A'"])
def test_missing_value_policies(fill_missing: str) -> None:
    result = clean_dataframe(
        pd.DataFrame({"value": [1, None]}),
        trim_text=False,
        fill_missing=fill_missing,
        strip_chars="",
        column_transformations={},
    )

    if fill_missing == "Drop Rows":
        assert result["value"].tolist() == [1.0]
    else:
        assert result["value"].tolist() == [1.0, "N/A"]


@pytest.mark.parametrize("filename", ["cleaner_test.csv", "cleaner_test.xlsx", "cleaner_test.xls"])
def test_generated_spreadsheet_fixtures_are_readable(filename: str) -> None:
    path = Path(__file__).parent.parent / "assets" / "test_files" / filename
    if path.suffix == ".csv":
        frame = pd.read_csv(path)
    else:
        frame = pd.read_excel(path, engine="calamine" if path.suffix == ".xls" else "openpyxl")

    result = clean_dataframe(
        frame,
        trim_text=True,
        fill_missing="Keep Missing",
        strip_chars="$,%",
        column_transformations={"email": "Extract Email"},
    )

    assert result["name"].tolist() == ["Alice", "Bob"]
    assert result["email"].tolist() == ["alice@example.com", "bob@example.com"]


FIXTURE_DIR = Path(__file__).parent.parent / "assets" / "test_files"


def test_benchmark_converts_csv_to_xlsx(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "tests").mkdir()
    monkeypatch.chdir(tmp_path)

    # Use run_benchmark from cleaner_benchmark.py since clean_dataframe
    # only cleans and not save
    run_benchmark(FIXTURE_DIR / "cleaner_test.csv", "xlsx", "test")

    output = tmp_path / "tests" / "benchmark_cleaned.xlsx"
    result = pd.read_excel(output, engine="calamine")

    assert output.is_file()
    assert result.shape == (2, 5)
    assert result.columns.tolist() == [
        "name",
        "name - First",
        "name - Last",
        "email",
        "amount",
    ]
    assert result["name"].tolist() == ["Alice", "Bob"]
    assert result["name - First"].tolist() == ["Alice", "Bob"]
    assert result["name - Last"].isna().all()
    assert result["email"].tolist() == ["alice@example.com", "bob@example.com"]
    assert result["amount"].tolist() == [200.00, 20]


def test_benchmark_converts_xlsx_to_csv(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "tests").mkdir()
    monkeypatch.chdir(tmp_path)

    # Use run_benchmark from cleaner_benchmark.py since clean_dataframe
    # only cleans and not save
    run_benchmark(FIXTURE_DIR / "cleaner_test.xlsx", "csv", "test")

    output = tmp_path / "tests" / "benchmark_cleaned.csv"
    result = pd.read_csv(output)

    assert output.is_file()
    assert result.shape == (2, 5)
    assert result.columns.tolist() == [
        "name",
        "name - First",
        "name - Last",
        "email",
        "amount",
    ]
    assert result["name"].tolist() == ["Alice", "Bob"]
    assert result["name - First"].tolist() == ["Alice", "Bob"]
    assert result["name - Last"].isna().all()
    assert result["email"].tolist() == ["alice@example.com", "bob@example.com"]
    assert result["amount"].tolist() == [200.00, 20]
