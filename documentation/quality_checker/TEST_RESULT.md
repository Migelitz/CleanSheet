# 🧪 Test Results

## Overview
This document records the test results for the **Cleansheet** data-quality checker.

The test suite verifies that the quality checker produces consistent and meaningful results when processing the same test dataset in different spreadsheet formats.

Current test fixtures:

- quality_test.csv
- quality_test.xlsx
- quality_test.xls

All three files contain the same logical test dataset and are intended to exercise the same data-quality checks across different input formats.

## Test Dataset

The test dataset contains several intentionally constructed conditions:

- Numeric columns containing positive, negative, and zero values.
- Missing values.
- A completely empty column.
- Categorical values.
- Sentinel values such as ?, missing, DK, #DIV/0!, 1970-01-01, valid_text, and -.
- Duplicate records.
- A deliberately mixed-type drift_test column to test type drift detection.
- Numeric values that transition to string values in later CSV chunks.

The dataset is intentionally designed to test both normal and problematic data conditions.

## Test Coverage

The test suite currently verifies:

- Dataset geometry.
- Column names.
- Empty-column detection.
- Baseline data types.
- Type drift detection.
- Null counts.
- Null percentages.
- Non-null counts.
- Non-null percentages.
- Sentinel detection.
- Numeric minimum and maximum values.
- Zero counts.
- Negative counts.
- Duplicate detection.
- Running sums.
- Numeric counts.
- Mean values.
- Population variance.
- Sample variance.
- Population standard deviation.
- Sample standard deviation.
- Population covariance.
- Sample covariance.
- Unique-value/cardinality detection.

## Results

The CSV test fixture passes the complete test suite, including the intentionally mixed-type **drift_test** behavior.

The XLSX and XLS fixtures pass the majority of the quality checks. Two assertions differ from the CSV expectations:

1. test_schema_integrity
2. test_categorical_cardinality

Both differences are caused by the same underlying behavior: **dtype inference differs between chunked CSV processing and whole-file Excel processing.**

## Known XLSX/XLS Difference

### Baseline dtype
For CSV files, the quality checker processes the data in chunks.

Because pandas performs dtype inference on each chunk, the intentionally mixed drift_test column can contain different Python/pandas types across chunks.

For example:

```text
Earlier chunk:
100
200
300
400

→ integer values

Later chunk:
500
600
700
800
text_drift

→ string values
```

As a result, the CSV test preserves the mixed-type behavior and reports:

```python
{
    "drift_test": np.dtype("int64")
}
```

as the baseline dtype while separately detecting the type drift.

**For XLSX/XLS files**, the worksheet is currently loaded as a complete dataset rather than being processed using the same chunk-level inference strategy.

Pandas therefore sees the complete **drift_test** column at once and represents the column as a string dtype because it contains **text_drift**.

The result is effectively:

```python
{
    "drift_test": pd.StringDtype(na_value=np.nan)
}
```

This causes the `test_schema_integrity` assertion to differ from the CSV expectation.

### Known Cardinality Difference
The same behavior affects `unique_values` for `drift_test`.

The CSV result intentionally preserves values with their chunk-level types:

```python
{
    100,
    200,
    300,
    400,
    "500",
    "600",
    "700",
    "800",
    "text_drift",
}
```

For XLSX/XLS, the entire column is inferred as strings, resulting in:

```python
{
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
```

Therefore `test_categorical_cardinality` differs for XLSX/XLS.

## Decision

These two differences are **accepted behavior** and are not currently considered defects.

The quality checker is primarily concerned with detecting data-quality characteristics rather than forcing every file format to produce identical pandas dtype representations.

The following important quality checks remain consistent across CSV, XLSX, and XLS:

- Dataset geometry.
- Column structure.
- Empty columns.
- Missingness.
- Sentinel values.
- Numeric health.
- Duplicate detection.
- Central tendency.
- Dispersion.
- Covariance.
- Other statistical calculations.

The only accepted format-dependent differences are the representation of the intentionally mixed-type drift_test column in:

- baseline_dtypes
- unique_values

## Why This Tradeoff Is Accepted

Making XLSX/XLS behave exactly like chunked CSV processing would require changing the Excel ingestion strategy solely to reproduce CSV's chunk-level dtype inference.

This is not currently necessary because:

1. The underlying data is still processed correctly.
2. The intentional type drift remains identifiable.
3. Numerical and statistical calculations remain correct.
4. Missingness and sentinel detection remain correct.
5. The difference is a consequence of the input-processing strategy rather than corrupted or lost data.
6. The behavior is documented and therefore known to the project.

The current implementation therefore favors **correct and practical quality analysis across multiple formats** over forcing identical pandas dtype representations.

## Conclusion

The current test results are considered acceptable.

CSV provides chunk-level dtype behavior, while XLSX/XLS use whole-file dtype inference. This creates two expected differences for the intentionally mixed `drift_test` column.

No change to the quality-checking implementation is required at this stage.

Future changes to the Excel ingestion strategy should revisit these tests and determine whether the expected dtype and cardinality behavior should be updated.

> **Status: Accepted — testing complete for CSV, XLSX, and XLS input compatibility.**