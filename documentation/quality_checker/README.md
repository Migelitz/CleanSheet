# Data Quality Checker

The **CleanSheet Data Quality Checker** is a spreadsheet-profiling engine designed to inspect datasets for common structural, missing-data, numeric, duplication, and statistical quality issues.

It is implemented as part of the CleanSheet desktop GUI and is intended primarily as a practical, customizable data-cleaning tool for personal use. The engine is also designed to remain usable on standard consumer hardware when processing larger CSV datasets.

The core analysis logic is implemented in:

```
src/cleansheet/quality/quality_checker.py
```

The GUI integration is handled by:

```
src/cleansheet/quality/tab_quality.py
```

---

## What Does It Check?

The Quality Checker produces a data-quality report containing several categories of information.

### Dataset Structure

- Total number of rows.
- Total number of columns.
- Column names.
- Completely empty columns.

### Schema & Type Integrity

- Baseline data types detected from the first CSV chunk or the loaded Excel dataset.
- Type-drift detection when a column is interpreted with different data types across CSV chunks.

### Missing Data

- Standard null values such as `NaN`, `None`, and other values recognized by Pandas.
- Null counts and percentages.
- Non-null counts and percentages.
- Detection of columns containing only missing values.

### Sentinel Values

The engine also searches for common placeholder values that may represent missing or invalid data but are not necessarily parsed as standard nulls.

Examples include:

```
?
N/A
missing
unknown
DK
REF
#DIV/0!
1970-01-01
-
```

The sentinel list is intentionally heuristic and can be expanded as additional domain-specific cases are encountered.

### Numeric Health

For numeric columns, the engine calculates:

- Minimum value.
- Maximum value.
- Number of zero values.
- Number of negative values.
- Number of valid numeric observations.
- Global sum.
- Mean.
- Population variance.
- Sample variance.
- Population standard deviation.
- Sample standard deviation.

### Duplicate Detection

Rows are hashed using Pandas' `hash_pandas_object()` and tracked globally to identify duplicate rows across the entire dataset, including duplicates that occur in different processing chunks.

### Pairwise Statistics

For numeric column pairs, the engine calculates:

- Sample covariance.
- Population covariance.
- Pearson correlation.

Only rows where both variables contain valid numeric observations contribute to pairwise calculations.

### Categorical Cardinality

The engine tracks distinct non-null values for columns while applying a configurable cardinality guardrail.

The current threshold is:

```
MAX_UNIQUE_VALUE = 1_000
```

Columns exceeding this threshold are classified as:

```
High Cardinality
```

This prevents large collections of unique strings from being retained unnecessarily.

---

## Input Formats

The Quality Checker currently accepts:

```
.csv
.xls
.xlsx
```

### CSV

CSV files are processed incrementally using Pandas chunking.

Conceptually:

```
CSV file
│
▼
Read chunk
│
▼
Analyze chunk
│
▼
Accumulate global statistics
│
▼
Read next chunk
│
▼
...
```

The production/default chunk size is **50,000 rows**.

Smaller chunk sizes may be used by tests or experiments. For example, the accuracy tests use a chunk size of 5 rows so that a deliberately mixed-type column can transition between chunks inside a very small fixture.

### Excel

Excel files currently use the `calamine` engine for ingestion.

The current implementation first loads the worksheet into a DataFrame and then slices that DataFrame into chunks for compatibility with the same analysis loop used by CSV processing.

Therefore, Excel processing is **not currently true out-of-core streaming**.

Conceptually:

```
Excel workbook
   │
   ▼
Load workbook into memory
   │
   ▼
DataFrame
   │
   ▼
Slice into analysis chunks
   │
   ▼
Run quality checks
```

This is an intentional v1 limitation. A future version may investigate a more genuinely streaming Excel ingestion strategy.

---

## Processing Philosophy

The engine uses a **single-pass accumulation model** wherever practical.

Instead of retaining the complete dataset for statistical calculations, it maintains running state such as:

```
sum(x)
sum(x²)
sum(xy)
count
minimum
maximum
```

This allows statistics to be calculated after processing the final chunk without requiring a second complete pass over the source file.

The approach keeps the implementation relatively simple and works naturally with the CSV chunk-processing model.

There are, however, known scalability boundaries. The engine does **not** guarantee globally constant memory usage because some forms of global state grow with the dataset or schema.

Examples include:

- The global duplicate hash set grows with the number of unique rows.
- Pairwise statistical state grows with the number of numeric column combinations.
- Excel ingestion currently requires the workbook to be loaded into memory first.
- Cardinality tracking intentionally retains up to the configured number of unique values per column.

These trade-offs are documented in more detail in `ARCHITECTURE_NOTES.md`.

---

## V1 Scope & Known Limitations

The Quality Checker is a **v1 profiling engine**, not a complete data-quality or statistical-analysis platform.

Several limitations are known and intentionally accepted for the current release.

### Duplicate Tracking

Duplicate detection uses a global Python `set` containing 64-bit row hashes.

This avoids retaining complete row data for duplicate comparison, but the set still grows with the number of unique rows.

Extremely large datasets with very high numbers of unique rows can therefore exhaust available memory.

This behavior was observed during testing with a dataset containing approximately 100 million rows.

See `ARCHITECTURE_NOTES.md` for the design rationale and `TEST_RESULT.md` for testing evidence.

### Excel Memory Usage

CSV processing benefits from incremental reading, while the current Excel implementation loads the workbook into memory before analysis.

Large Excel workbooks can therefore consume substantially more memory than similarly sized CSV datasets.

### Statistical Numerical Stability

Variance and covariance currently use algebraic shortcut formulas based on accumulated sums and squared/cross-product sums.

These formulas are efficient and convenient for a single-pass implementation but can suffer from floating-point cancellation on datasets containing extremely large values with relatively small variance.

A numerically more stable online approach, such as Welford-style accumulation, is a candidate for a future version.

### Pairwise Covariance Scaling

Pairwise statistics are calculated eagerly for every combination of numeric columns:

$$
\binom{K}{2}
$$

where $K$ is the number of numeric columns.

Consequently, the amount of pairwise work increases quadratically as the number of numeric columns grows.

A future implementation may make expensive pairwise calculations optional or on-demand.

### Sentinel Detection

Sentinel detection is heuristic.

There is no universal list of strings that represents missing data across every spreadsheet, organization, or domain. The current list covers a collection of common placeholders, spreadsheet errors, refusal codes, and date placeholders but cannot guarantee detection of every domain-specific sentinel.

### Cardinality Tracking

The current 1,000-value threshold is a deliberate memory guardrail rather than an empirically established universal optimum.

The threshold can be revisited as more datasets and usage patterns are evaluated.

---

## Documentation

The Quality Checker documentation is separated by purpose.

### Architecture

`ARCHITECTURE_NOTES.md`

Explains the engineering decisions behind the implementation, including:

- CSV chunking.
- Excel ingestion.
- Running statistical accumulators.
- Duplicate hashing.
- Pairwise covariance.
- Cardinality limits.
- Sentinel detection.
- Memory and scalability trade-offs.
- Known boundaries and future improvements.

### Test Results

`TEST_RESULT.md`

Documents the correctness tests performed against CSV, XLSX, and XLS fixtures, including the intentionally mixed-type test cases and accepted format-specific differences.

### Troubleshooting

`TROUBLESHOOTING.md`

Documents implementation problems encountered during development and the solutions or workarounds used to resolve them.

---

## Summary

The CleanSheet Quality Checker is designed around a simple goal:

> **Provide useful spreadsheet-quality profiling without requiring the entire dataset to remain in memory during CSV analysis.**

The current v1 implementation deliberately favors:

- Standard Pandas functionality.
- Straightforward single-pass processing.
- Compatibility with the CleanSheet desktop GUI.
- Practical profiling over exhaustive statistical analysis.
- Simple implementation over premature optimization.
- Explicitly documented limitations over hidden assumptions.

The engine is intended to evolve as additional datasets, benchmarks, and real-world usage reveal where the current design should be improved.