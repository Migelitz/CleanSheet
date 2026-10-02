# CleanSheet Test Results

## 1. Testing Scope

This document records the functional, integration, manual GUI, and performance/resource testing performed on the CleanSheet spreadsheet-cleaning functionality.

The purpose of the testing was to verify that:

* Cleaning transformations produce the expected results.
* Missing-value policies behave correctly.
* Spreadsheet fixtures can be processed.
* CSV/XLSX conversion paths produce valid output.
* The GUI's major cleaner workflows operate correctly through manual testing.
* The CSV chunk-processing pipeline performs correctly under a larger dataset.
* Resource usage can be observed under a repeatable stress-test workload.

Passing these tests does **not** establish that CleanSheet is free of all possible bugs or that it will behave identically for every possible spreadsheet.

---

# 2. Test Environment

The primary benchmark machine was:

| Component         | Specification                     |
| ----------------- | --------------------------------- |
| OS                | Linux Mint 22.3 Zena              |
| Desktop           | Xfce 4.18.1                       |
| Kernel            | 7.0.0-34-generic                  |
| CPU               | Intel Core i5-1035G1              |
| CPU configuration | 4 physical cores / 8 logical CPUs |
| RAM               | 8 GB                              |
| Python            | 3.12                              |
| Architecture      | x86_64                            |
| Storage           | ~477 GB SSD                       |

CPU usage was intentionally constrained during sustained benchmarking to avoid excessive thermal load.

At approximately 85% CPU usage, the laptop reached around **98–100°C** during prolonged testing. Testing around the selected 60% limit kept temperatures approximately around **80–87°C**.

The benchmark's reported `psutil` process CPU percentages can exceed 100% because process CPU utilization is measured across logical CPUs.

---

# 3. Automated Functional Tests

The automated test suite verifies the core `clean_dataframe()` functionality.

## Results

All automated tests passed.

### Covered functionality

| Test Area                       | Result |
| ------------------------------- | ------ |
| Text trimming                   | PASS   |
| Character stripping             | PASS   |
| Lowercase transformation        | PASS   |
| Uppercase transformation        | PASS   |
| Title Case transformation       | PASS   |
| Numbers Only transformation     | PASS   |
| Currency cleaning               | PASS   |
| Email extraction                | PASS   |
| URL extraction                  | PASS   |
| Email anonymization             | PASS   |
| Number anonymization            | PASS   |
| Date normalization              | PASS   |
| Human-name splitting            | PASS   |
| Missing human-name components   | PASS   |
| Drop Rows missing-value policy  | PASS   |
| Fill `N/A` missing-value policy | PASS   |

The tests use parameterization where multiple transformations follow the same testing pattern.

---

# 4. Spreadsheet Fixture Tests

Generated spreadsheet fixtures were used to verify that the cleaner can process equivalent test data stored in different spreadsheet formats.

The fixtures included:

* CSV
* XLSX
* XLS

All three contained equivalent test data.

The tests verified that the expected name and email transformations were produced.

### Result

**PASS**

The CSV, XLSX, and XLS fixtures were successfully read and processed.

---

# 5. Integration Tests

The benchmark pipeline was also tested as part of the automated test suite.

## CSV → XLSX

The test verified:

* Output file creation
* Output readability
* Expected row count
* Expected column structure
* Human-name splitting
* Email extraction
* Currency conversion

### Result

**PASS**

Expected output:

```text
Rows: 2
Columns: 5

name
name - First
name - Last
email
amount
```

---

## XLSX → CSV

The same type of validation was performed for the reverse conversion.

### Result

**PASS**

Expected output structure and values were produced successfully.

---

# 6. Manual GUI QA

The cleaner was manually tested through the actual GUI.

The following workflows were tested:

| Manual Test            | Result |
| ---------------------- | ------ |
| File selection         | PASS   |
| Drag-and-drop          | PASS   |
| Column transformations | PASS   |
| Missing-value options  | PASS   |
| Duplicate removal      | PASS   |
| Export                 | PASS   |
| Invalid input handling | PASS   |

These tests were performed manually rather than through an automated GUI-testing framework.

---

# 7. Stress Benchmark

The stress benchmark was designed to measure:

* Execution time
* Processing throughput
* Peak process RSS
* Python heap usage
* Average CPU usage
* Peak CPU usage
* Output size

The benchmark was run three times for each major file format.

## Test Dataset

The stress-test dataset contained:

* **60,000 rows**
* **15 columns**
* Synthetic/generated test data

The CSV input size was approximately **14.93 MB**.

The XLSX input size was approximately **4.70 MB**.

The dataset contained fields representing different transformation types, including:

```text
name
email
url
phone
currency
event_date
lower_text
upper_text
title_text
private_email
account_number
missing_value
row_group
```

The generated data intentionally contained values suitable for testing the different transformation operations.

The 60,000-row CSV dataset also crosses the current 50,000-row chunk boundary:

```text
Chunk 1: 50,000 rows
Chunk 2: 10,000 rows
```

Therefore, the benchmark exercises the multi-chunk CSV processing path.

---

# 8. CSV Benchmark

Input:

```text
cleaner_stress_test.csv
Size: 14.93 MB
Rows: 60,000
```

| Metric           |     Run 1 |     Run 2 |     Run 3 |
| ---------------- | --------: | --------: | --------: |
| Time             |  84.094 s |  82.158 s |  84.719 s |
| Rows/sec         |       713 |       730 |       708 |
| MB/sec           |      0.18 |         — |         — |
| Peak RSS         | 385.56 MB | 424.55 MB | 441.29 MB |
| Python heap peak | 130.55 MB | 130.37 MB | 130.21 MB |
| Avg CPU          |    101.0% |    100.6% |    100.9% |
| Peak CPU         |    499.5% |    158.2% |    551.7% |

Output size for Run 1 was approximately **13.19 MB**.

The CSV processing time remained relatively consistent across the three runs, with all runs completing in approximately 82–85 seconds.

---

# 9. XLSX Benchmark

Input:

```text
cleaner_stress_test.xlsx
Size: 4.70 MB
Rows: 60,000
```

| Metric           |     Run 1 |     Run 2 |     Run 3 |
| ---------------- | --------: | --------: | --------: |
| Time             | 145.272 s | 147.690 s | 146.990 s |
| Rows/sec         |       413 |       406 |       408 |
| MB/sec           |      0.03 |         — |         — |
| Peak RSS         | 575.77 MB | 636.18 MB | 675.68 MB |
| Python heap peak | 198.39 MB | 196.02 MB | 196.01 MB |
| Avg CPU          |    100.7% |    100.4% |    101.0% |
| Peak CPU         |    726.5% |    150.3% |    911.2% |

Output size was approximately **5.63 MB** for the first run.

The XLSX path remained relatively consistent in execution time, completing in approximately 145–148 seconds.

For this workload, the XLSX path processed roughly **406–413 rows/sec**, compared with approximately **708–730 rows/sec** for the CSV path.

---

# 10. Resource Usage Observations

## CSV

Across the three CSV runs:

* Python heap peak remained around **130 MB**.
* Peak process RSS ranged from approximately **386 MB to 441 MB**.
* Processing time remained around **82–85 seconds**.

## XLSX

Across the three XLSX runs:

* Python heap peak remained around **196–198 MB**.
* Peak process RSS ranged from approximately **576 MB to 676 MB**.
* Processing time remained around **145–148 seconds**.

The XLSX workflow therefore used substantially more peak process memory than the CSV workflow for this particular dataset.

This is consistent with the architecture: CSV → CSV is processed in chunks, while the Excel path currently loads the complete dataset into memory.

---

# 11. Important Benchmark Methodology Note

The benchmark runs were executed within the same Python process.

As a result, the process's baseline RSS increased between repeated runs. For example, memory allocated during one run may remain available to the Python process for reuse rather than immediately returning to the operating system.

Therefore:

```text
Peak RSS
```

is more useful for comparing the observed memory footprint than:

```text
Peak RSS - run-start RSS
```

The latter was still recorded, but it should not be interpreted as a clean measurement of the total memory required by the application.

The benchmark therefore does **not** claim that CleanSheet simply "uses X MB of RAM."

Instead, the documented result is that the process reached the measured peak RSS values under the stated workload and test environment.

---

# 12. CPU Measurement Note

The benchmark uses `psutil.Process.cpu_percent()` to monitor process CPU usage.

Process CPU utilization can exceed 100% when multiple logical CPUs are being utilized.

For example:

```text
100% ≈ one fully utilized logical CPU
200% ≈ two fully utilized logical CPUs
...
```

Therefore, peak measurements such as:

```text
499.5%
726.5%
911.2%
```

do not mean that the system somehow exceeded a 100% CPU limit.

The benchmark's sustained CPU condition was separately constrained to approximately 60% to keep the laptop's temperature within a more suitable range for prolonged testing.

---

# 13. Duplicate Benchmarking Limitation

The current stress-test dataset contains no duplicate rows. Therefore, the benchmark exercises the cross-chunk deduplication mechanism with unique rows but does not measure how its resource usage changes at different duplicate rates.

The current implementation maintains a seen_hashes set containing hashes of previously encountered unique rows. As the number of unique rows increases, this set is expected to grow. Conversely, a dataset containing more repeated rows should produce fewer unique hashes. However, the memory and runtime effects of this behavior have not yet been measured.

The memory and processing overhead of Pandas' drop_duplicates() has also not been independently benchmarked under different duplicate rates.

Future testing should measure different scenarios, such as:

```text
0% duplicates
Low duplicate rate
Moderate duplicate rate
High duplicate rate
Very high duplicate rate
```

and compare:

* execution time
* peak RSS
* Python heap
* hash-set size
* output size

This is intentionally recorded as a future performance investigation rather than as a current benchmark conclusion.

---

# 14. Other Testing Limitations

The current test suite does not comprehensively cover every possible GUI or data-processing scenario.

Not currently covered by automated tests:

* GUI interaction automation
* Drag-and-drop automation
* Progress indicator behavior
* GUI responsiveness under automated testing
* Large-scale XLS/XLSX testing beyond the documented benchmark
* Extremely large CSV datasets
* Many-chunk CSV datasets
* Different CSV encodings and delimiters
* Every possible malformed spreadsheet
* Hash collision scenarios
* Comprehensive duplicate-rate benchmarking
* Fuzzy duplicate detection

The current testing should therefore be understood as validation of the implemented v1.0.0 scope rather than proof of complete correctness for arbitrary input.

---

# 15. Overall Observations

The testing produced several useful observations.

### Functional behavior

The automated functional tests passed for the implemented cleaning operations.

### Spreadsheet compatibility

The tested CSV, XLSX, and XLS fixtures were successfully processed.

### Integration

The tested CSV → XLSX and XLSX → CSV pipelines produced the expected output.

### GUI

The main cleaner workflows tested manually operated successfully.

### CSV scalability approach

The 60,000-row CSV benchmark exercised the two-chunk processing path and maintained relatively consistent execution times across three runs.

### Excel limitation

The XLSX path required substantially more peak memory than the CSV chunked path for the tested workload, supporting the architectural decision to treat scalable Excel processing as a future improvement.

---

# 16. Final QA Verdict

## v1.0.0 — PASS for tested scope

CleanSheet's spreadsheet-cleaning functionality **passed the automated functional tests, spreadsheet integration tests, manual GUI checks, and documented stress benchmark runs** performed for this QA cycle.

The results support the current v1.0.0 implementation and its intended workflow.

However, this verdict applies only to the tested scope.

It does not mean that:

* all possible spreadsheet inputs are supported,
* all edge cases have been tested,
* large Excel files can be processed efficiently,
* cross-chunk duplicate tracking has been fully benchmarked,
* or the application is guaranteed to be free of undiscovered bugs.

The current version should therefore be considered **validated for the tested functionality, with known limitations documented for future development.**

---

# 17. Future QA

Future testing should prioritize:

1. Larger CSV datasets with many more chunks.
2. Different CSV chunk sizes.
3. Duplicate-rate stress testing.
4. Memory overhead of cross-chunk hash tracking.
5. Larger XLS/XLSX datasets.
6. Alternative Excel processing approaches.
7. Automated GUI testing.
8. Additional malformed and unusual spreadsheet inputs.
9. Repeated-process benchmark isolation to obtain cleaner memory comparisons.
10. Performance testing after future optimization changes.

These tests can be added as the cleaner evolves beyond v1.0.0.
