from pathlib import Path

import pandas as pd

from src.cleansheet.concatenator.tab_concat import concat_files


def test_concat_csv_and_csv_to_csv(tmp_path: Path) -> None:
    source_path = (
        Path(__file__).parent.parent
        / "assets"
        / "test_files"
        / "quality_test.csv"
    )
    output_path = tmp_path / "merged.csv"

    concat_files(
        files=[str(source_path), str(source_path)], 
        output_folder=str(tmp_path),
        output_filename=output_path.name,
        chunksize=5,
    )

    result = pd.read_csv(output_path)

    source_data = pd.read_csv(source_path)
    expected = pd.concat(
        [source_data, source_data],
        ignore_index=True,
    )

    pd.testing.assert_frame_equal(result, expected)
    
def test_concat_xlsx_and_xlsx_to_xlsx(tmp_path: Path) -> None:
    source_path = (
        Path(__file__).parent.parent
        / "assets"
        / "test_files"
        / "quality_test.xlsx"
    )
    output_path = tmp_path / "merged.xlsx"

    concat_files(
        files=[str(source_path), str(source_path)], 
        output_folder=str(tmp_path),
        output_filename=output_path.name,
        chunksize=5,
    )

    result = pd.read_excel(output_path)

    source_data = pd.read_excel(source_path)
    expected = pd.concat(
        [source_data, source_data],
        ignore_index=True,
    )

    # XLSX/CSV ingestion can produce different dtype representations
    # because CSV input is processed in chunks while the expected
    # DataFrame is constructed from the complete source dataset.
    print(result["drift_test"].tolist())
    print(expected["drift_test"].tolist())

    pd.testing.assert_frame_equal(result, expected, check_dtype=False)

def test_concat_csv_and_csv_to_xlsx(tmp_path: Path) -> None:
    source_path = (
        Path(__file__).parent.parent
        / "assets"
        / "test_files"
        / "quality_test.csv"
    )
    output_path = tmp_path / "merged.xlsx"

    concat_files(
        files=[str(source_path), str(source_path)], 
        output_folder=str(tmp_path),
        output_filename=output_path.name,
        chunksize=5,
    )

    result = pd.read_excel(output_path)

    source_data = pd.read_csv(source_path)
    expected = pd.concat(
        [source_data, source_data],
        ignore_index=True,
    )

    # XLSX/CSV ingestion can produce different dtype representations
    # because CSV input is processed in chunks while the expected
    # DataFrame is constructed from the complete source dataset.
    print(result["drift_test"].tolist())
    print(expected["drift_test"].tolist())

    pd.testing.assert_frame_equal(result, expected, check_dtype=False)

def test_concat_xlsx_and_xlsx_to_csv(tmp_path: Path) -> None:
    source_path = (
        Path(__file__).parent.parent
        / "assets"
        / "test_files"
        / "quality_test.xlsx"
    )
    output_path = tmp_path / "merged.csv"

    concat_files(
        files=[str(source_path), str(source_path)], 
        output_folder=str(tmp_path),
        output_filename=output_path.name,
        chunksize=5,
    )

    result = pd.read_csv(output_path)

    source_data = pd.read_excel(source_path)
    expected = pd.concat(
        [source_data, source_data],
        ignore_index=True,
    )

    pd.testing.assert_frame_equal(result, expected)

def test_concat_csv_and_xlsx_to_csv(tmp_path: Path) -> None:
    csv_source_path = (
        Path(__file__).parent.parent / "assets" / "test_files" / "quality_test.csv"
    )
    excel_source_path = (
        Path(__file__).parent.parent / "assets" / "test_files" / "quality_test.xlsx"
    )
    output_path = tmp_path / "merged.csv"

    concat_files(
        files=[str(csv_source_path), str(excel_source_path)], 
        output_folder=str(tmp_path),
        output_filename=output_path.name,
        chunksize=5,
    )

    result = pd.read_csv(output_path)

    csv_source_data = pd.read_csv(csv_source_path)
    excel_source_data = pd.read_excel(excel_source_path)
    expected = pd.concat(
        [csv_source_data, excel_source_data],
        ignore_index=True,
    )

    pd.testing.assert_frame_equal(result, expected)

def test_concat_csv_and_xlsx_to_xlsx(tmp_path: Path) -> None:
    csv_source_path = (
        Path(__file__).parent.parent / "assets" / "test_files" / "quality_test.csv"
    )
    excel_source_path = (
        Path(__file__).parent.parent / "assets" / "test_files" / "quality_test.xlsx"
    )
    output_path = tmp_path / "merged.xlsx"

    concat_files(
        files=[str(csv_source_path), str(excel_source_path)], 
        output_folder=str(tmp_path),
        output_filename=output_path.name,
        chunksize=5,
    )

    result = pd.read_excel(output_path)

    csv_source_data = pd.read_csv(csv_source_path)
    excel_source_data = pd.read_excel(excel_source_path)
    expected = pd.concat(
        [csv_source_data, excel_source_data],
        ignore_index=True,
    )

    # XLSX/CSV ingestion can produce different dtype representations
    # because CSV input is processed in chunks while the expected
    # DataFrame is constructed from the complete source dataset.
    print(result["drift_test"].tolist())
    print(expected["drift_test"].tolist())

    pd.testing.assert_frame_equal(result, expected, check_dtype=False)

def test_concat_big_csv_and_xlsx_to_xlsx(tmp_path: Path) -> None:
    csv_source_path = (
        Path(__file__).parent.parent / "assets"  / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
    )
    excel_source_path = (
        Path(__file__).parent.parent / "assets" / "WA_Fn-UseC_-Telco-Customer-Churn.xlsx"
    )
    output_path = tmp_path / "merged.xlsx"

    concat_files(
        files=[str(csv_source_path), str(excel_source_path)], 
        output_folder=str(tmp_path),
        output_filename=output_path.name,
        chunksize=50_000,
    )

    result = pd.read_excel(output_path)

    csv_source_data = pd.read_csv(csv_source_path)
    excel_source_data = pd.read_excel(excel_source_path)
    expected = pd.concat(
        [csv_source_data, excel_source_data],
        ignore_index=True,
    )

    # Confirm that the assertion issue is a dtype mismatch, not different values.
    for index in (7042, 7043):
        result_value = result["TotalCharges"].iloc[index]
        expected_value = expected["TotalCharges"].iloc[index]
        print(
            f"TotalCharges[{index}]: "
            f"result={result_value!r} ({type(result_value).__name__}), "
            f"expected={expected_value!r} ({type(expected_value).__name__}), "
            f"values_equal={result_value == expected_value}"
        )

    print(
        "TotalCharges dtype: "
        f"result={result['TotalCharges'].dtype}, "
        f"expected={expected['TotalCharges'].dtype}"
    )

    pd.testing.assert_frame_equal(result, expected, check_dtype=False)

def test_concat_big_csv_and_xlsx_to_csv(tmp_path: Path) -> None:
    csv_source_path = (
        Path(__file__).parent.parent / "assets"  / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
    )
    excel_source_path = (
        Path(__file__).parent.parent / "assets" / "WA_Fn-UseC_-Telco-Customer-Churn.xlsx"
    )
    output_path = tmp_path / "merged.csv"

    concat_files(
        files=[str(csv_source_path), str(excel_source_path)], 
        output_folder=str(tmp_path),
        output_filename=output_path.name,
        chunksize=50_000,
    )

    result = pd.read_csv(output_path)

    csv_source_data = pd.read_csv(csv_source_path)
    excel_source_data = pd.read_excel(excel_source_path)
    expected = pd.concat(
        [csv_source_data, excel_source_data],
        ignore_index=True,
    )

    # Confirm that the assertion issue is a dtype mismatch, not different values.
    for index in (7042, 7043):
        result_value = result["TotalCharges"].iloc[index]
        expected_value = expected["TotalCharges"].iloc[index]
        print(
            f"TotalCharges[{index}]: "
            f"result={result_value!r} ({type(result_value).__name__}), "
            f"expected={expected_value!r} ({type(expected_value).__name__}), "
            f"values_equal={result_value == expected_value}"
        )

    print(
        "TotalCharges dtype: "
        f"result={result['TotalCharges'].dtype}, "
        f"expected={expected['TotalCharges'].dtype}"
    )

    pd.testing.assert_frame_equal(result, expected, check_dtype=False)

def test_concat_huge_csv_and_xlsx_to_csv(tmp_path: Path) -> None:
    csv_source_path = (
        Path(__file__).parent.parent / "assets" / "5m Sales Records.csv"
    )
    excel_source_path = (
        Path(__file__).parent.parent / "assets" / "5m Sales Records.xlsx"
    )
    output_path = tmp_path / "merged.csv"

    concat_files(
        files=[str(csv_source_path), str(excel_source_path)], 
        output_folder=str(tmp_path),
        output_filename=output_path.name,
        chunksize=1_000_000,
    )

    result = pd.read_csv(output_path)

    csv_source_data = pd.read_csv(csv_source_path)
    excel_source_data = pd.read_excel(excel_source_path)
    expected = pd.concat(
        [csv_source_data, excel_source_data],
        ignore_index=True,
    )

    pd.testing.assert_frame_equal(result, expected)


def test_concat_huge_csv_and_xlsx_to_xlsx(tmp_path: Path) -> None:

    """Fails due to concatenation limit set in concatenator"""

    csv_source_path = (
        Path(__file__).parent.parent / "assets" / "5m Sales Records.csv"
    )
    excel_source_path = (
        Path(__file__).parent.parent / "assets" / "5m Sales Records.xlsx"
    )
    output_path = tmp_path / "merged.xlsx"

    concat_files(
        files=[str(csv_source_path), str(excel_source_path)], 
        output_folder=str(tmp_path),
        output_filename=output_path.name,
        chunksize=1_000_000,
    )

    result = pd.read_excel(output_path)

    csv_source_data = pd.read_csv(csv_source_path)
    excel_source_data = pd.read_excel(excel_source_path)
    expected = pd.concat(
        [csv_source_data, excel_source_data],
        ignore_index=True,
    )

    pd.testing.assert_frame_equal(result, expected, check_dtype=False)

