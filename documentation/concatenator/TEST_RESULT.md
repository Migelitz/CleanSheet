# 🧪 Test Results

This document records the current functional tests, performance benchmarks, observed behavior, and accepted limitations of the **Spreadsheet Concatenator**.

The purpose of these tests is not to prove that the Concatenator is universally optimal.

Instead, they establish what the current V1 implementation does under the tested workloads and hardware conditions.

---

# Overview

Testing was divided into two major categories:

1. **Functional testing**
2. **Performance and memory benchmarking**

Functional testing verifies that the supported CSV/XLSX combinations produce the expected datasets.

Benchmarking evaluates:

* Execution time
* Throughput
* Peak Python-tracked memory
* Peak process RSS
* CPU behavior
* Effect of chunk size
* Effect of input/output format and workload characteristics

The benchmarks are intended as an engineering baseline for V1 rather than as universal performance guarantees.

---

# 🧪 Functional Test Coverage

The current functional suite covers the six primary format combinations.

| Test | Input       | Output | Result |
| ---- | ----------- | ------ | -----: |
| 1    | CSV + CSV   | CSV    | ✅ Pass |
| 2    | XLSX + XLSX | XLSX   | ✅ Pass |
| 3    | CSV + CSV   | XLSX   | ✅ Pass |
| 4    | XLSX + XLSX | CSV    | ✅ Pass |
| 5    | CSV + XLSX  | CSV    | ✅ Pass |
| 6    | CSV + XLSX  | XLSX   | ✅ Pass |

Tests use `pytest` and Pandas dataframe comparisons.

Temporary test directories are provided using `tmp_path`, allowing pytest to clean the generated test files after execution.

---

# 🐛 Previously Discovered XLSX Writing Bug

During testing, the XLSX output path previously produced an incorrect number of rows when data was split across multiple chunks.

A test expected:

```text
20 rows
```

but the generated workbook contained:

```text
19 rows
```

The problem was caused by incorrect interaction between:

* `startrow`
* Header placement
* Multiple chunk writes

The second chunk was positioned incorrectly and overwrote an existing data row.

The writing logic was corrected so that:

* The header is written only once.
* The first chunk starts at the correct row.
* Subsequent chunks account for the header offset.

This demonstrates why multi-chunk output testing is important even when individual chunks appear correct.

---

# 🔬 Data Type Difference in Mixed-Format Testing

A larger test using the Telco Customer Churn dataset exposed a representation difference in the `TotalCharges` column.

The dataset contains approximately:

```text
7,043 rows
21 columns
```

When CSV and XLSX representations were combined, values such as:

```text
29.85
```

could appear as:

```text
"29.85"
```

in one processing path and:

```text
29.85
```

in another.

The difference appeared at the boundary between the input files, which is consistent with the different datatype inference behavior of the input formats.

---

# Why This Is Accepted

The Concatenator's responsibility is:

> **Concatenate files without intentionally transforming their data.**

Automatically converting all numeric-looking strings into numeric values could damage identifiers such as:

```text
000123
```

Therefore, the project intentionally does not perform aggressive datatype normalization.

`check_dtype=False` also does not solve the entire issue because it relaxes dtype metadata checks but does not make a string value and a numeric value equivalent.

The behavior is therefore documented and accepted for V1.

A future cleaning/normalization feature may address this separately.

---

# 💻 Benchmark Environment

The large CSV benchmarks were performed on the developer's Linux laptop.

The benchmark environment was intentionally controlled to reduce thermal stress.

Long CSV benchmark runs used approximately:

```text
intel_pstate max performance cap: 60%
```

The purpose was to avoid sustaining CPU temperatures close to 100 °C during repeated long-running tests.

Observed temperatures under the controlled configuration were approximately:

```text
78–92 °C
```

with observed averages around the mid-80 °C range.

A higher performance cap of approximately 85% produced observed temperatures around:

```text
98–100 °C
```

during sustained work, so the higher cap was not used for the long-running benchmark suite.

These results therefore represent:

> **The current device under a thermal-conscious CPU performance cap.**

They should not be interpreted as maximum possible hardware performance.

A faster or better-cooled machine can produce different absolute execution times.

The CPU cap is also part of the benchmark methodology: execution time is affected not only by the software workload but also by the available CPU performance of the test environment.

---

# 📈 Benchmark Metrics

The benchmark records:

* Total execution time
* Rows processed
* Rows/second
* Input MB/second
* Peak Python-tracked memory using `tracemalloc`
* Peak process RSS using `psutil`
* Average process CPU usage

Peak RSS is particularly important because it represents the process's overall resident memory rather than only Python allocations tracked by `tracemalloc`.

For repeated runs, **Peak Process RSS is the primary memory metric**.

The benchmark's **OS baseline RSS** and **Net OS RAM Used** values are still useful as diagnostic measurements, but they must be interpreted carefully because multiple repetitions are executed sequentially inside the same Python process. Memory retained or reused by the Python runtime and underlying libraries can cause the baseline to rise between runs.

Therefore, a higher baseline in a later repetition does not by itself mean that the Concatenator accumulated the previous workload's complete memory footprint.

---

# 🔁 Repeated-Run Methodology

The benchmark can execute several repetitions using a loop inside one Python process.

Conceptually:

```text
Python process
    ↓
Run 1
    ↓
Run 2
    ↓
Run 3
```

This is useful for observing repeatability, but it is not equivalent to launching each benchmark in a completely fresh interpreter.

The process remains alive between repetitions, so Python allocators and native libraries may retain or reuse memory. The post-processing `check_quality()` call is also outside the timed benchmark section, but retained allocations can still affect the baseline of a later repetition.

Because of this, the following are treated differently:

* **Peak RSS** — primary indicator of the maximum memory reached during the workload.
* **Python Heap Peak** — primary indicator of Python-level allocations tracked during that run.
* **Baseline RSS** — environmental/process-state information before that repetition.
* **Net RSS** — diagnostic information that is not directly comparable between repetitions when the process baseline changes.

This does not invalidate the V1 benchmarks. It simply defines what the measurements can and cannot establish.

A fresh-process benchmark suite could produce cleaner baseline comparisons, but the current V1 benchmark is accepted as an engineering characterization of the implementation under the documented test procedure.

---

# Dataset A — Large CSV

Input:

```text
5m Sales Records.csv × 2
```

Approximate combined input size:

```text
1.19 GB
```

Combined rows:

```text
10,000,000
```

Columns:

```text
14
```

This workload was selected to stress large CSV processing.

---

## Chunk Size: 5,000,000

| Run |      Time | Rows/s | MB/s |
| --: | --------: | -----: | ---: |
|   1 | 759.746 s | 13,162 | 1.57 |
|   2 | 756.893 s | 13,212 | 1.57 |
|   3 | 753.167 s | 13,277 | 1.58 |

Memory:

```text
Peak Python heap: ~1,328 MB
Peak RSS: ~1,889 MB
Net RSS: ~1,819 MB
```

Average CPU:

```text
~101.5–101.8%
```

---

## Chunk Size: 1,000,000

| Run |      Time | Rows/s | MB/s |
| --: | --------: | -----: | ---: |
|   1 | 744.429 s | 13,433 | 1.60 |
|   2 | 754.013 s | 13,262 | 1.58 |
|   3 | 749.282 s | 13,346 | 1.59 |

Memory:

```text
Peak Python heap: ~267 MB
Peak RSS: ~464 MB
Net RSS: ~394 MB
```

Average CPU:

```text
~101.7–101.9%
```

### Observation

The two chunk sizes produced broadly similar throughput.

However, memory usage differed dramatically.

The 1,000,000-row configuration reduced peak Python-tracked memory from approximately:

```text
1,328 MB
```

to:

```text
267 MB
```

and peak RSS from approximately:

```text
1,889 MB
```

to:

```text
464 MB
```

The runtime difference is small relative to the size of the workload and does not establish that 1,000,000 rows is inherently faster.

The stronger conclusion is:

> **The chunk size had a much larger effect on memory than on throughput in this workload.**

This demonstrates the central purpose of chunking: memory usage can be controlled without requiring the entire CSV dataset to exist in memory at once.

---

# Dataset B — String-Heavy CSV

Input:

```text
vehicles.csv × 2
```

Approximate combined input size:

```text
2.762 GB
```

Combined rows:

```text
853,760
```

Columns:

```text
26
```

This dataset was intentionally selected because it is large and string-heavy.

The larger amount of string-oriented data also demonstrates that raw file size and row count alone do not completely describe a workload's memory behavior. Cell contents and their resulting in-memory representations also matter.

---

# Chunk Size: 100,000

| Run |      Time | Rows/s |  MB/s |
| --: | --------: | -----: | ----: |
|   1 | 183.413 s |  4,655 | 15.06 |
|   2 | 182.071 s |  4,689 | 15.17 |
|   3 | 178.443 s |  4,785 | 15.48 |

Memory:

```text
Peak Python heap: ~1,766 MB
Peak RSS: ~2,082 MB
Net RSS: ~2,012 MB
```

---

# Chunk Size: 200,000

| Run |      Time | Rows/s |  MB/s |
| --: | --------: | -----: | ----: |
|   1 | 181.880 s |  4,694 | 15.18 |
|   2 | 181.296 s |  4,709 | 15.23 |
|   3 | 180.782 s |  4,723 | 15.28 |

Memory:

```text
Peak Python heap: ~3,393 MB
Peak RSS: ~3,777 MB
Net RSS: ~3,707 MB
```

---

# Chunk Size: 50,000

| Run |      Time | Rows/s |  MB/s |
| --: | --------: | -----: | ----: |
|   1 | 179.715 s |  4,751 | 15.37 |
|   2 | 177.583 s |  4,808 | 15.55 |
|   3 | 178.204 s |  4,791 | 15.50 |

Memory:

```text
Peak Python heap: ~957 MB
Peak RSS: ~1,241 MB
Net RSS: ~1,171 MB
```

Average CPU:

```text
~99.6–100.3%
```

---

# Chunk Size Comparison

The approximate results show:

| Chunk Size | Peak RSS | Average Runtime |
| ---------: | -------: | --------------: |
|     50,000 | ~1.24 GB |        ~178.5 s |
|    100,000 | ~2.08 GB |        ~181.3 s |
|    200,000 | ~3.78 GB |        ~181.3 s |

### Observation

Increasing the chunk size caused a substantial increase in memory usage.

However, runtime remained broadly similar.

The 50,000-row configuration happened to be slightly faster in these runs, but the test does not establish that smaller chunks are inherently faster.

Run-to-run variation and system conditions can affect execution time.

### Conclusion

The most defensible conclusion is:

> **For this workload, chunk size behaves primarily as a memory-control parameter rather than a reliable speed-control parameter.**

Increasing chunk size beyond a certain point produced diminishing performance returns while substantially increasing RAM usage.

---

# Dataset C — XLSX

Input:

```text
100mb.xlsx × 3
```

Approximate combined size:

```text
302 MB
```

Combined rows:

```text
81,000
```

Columns:

```text
8
```

The XLSX benchmark tested chunk sizes:

```text
50,000
80,000
100,000
```

---

# XLSX Benchmark Results

Execution times were approximately:

```text
7.26–7.85 seconds
```

Throughput was approximately:

```text
10,300–11,200 rows/s
38.5–41.7 MB/s
```

Peak Python-tracked memory was approximately:

```text
97 MB
```

Peak RSS was approximately:

```text
644 MB
```

Average CPU usage was approximately:

```text
98–106%
```

One recorded peak CPU value reached approximately:

```text
852.5%
```

This value is not treated as a meaningful representation of normal sustained CPU usage because `psutil.Process.cpu_percent()` is a stateful metric and process CPU percentages can exceed 100% on multicore systems.

The relatively short runtime of this workload also made it useful for demonstrating that execution speed is partly dependent on CPU performance. A different CPU performance limit or a different machine can produce a different absolute execution time even when the software and input dataset remain unchanged.

---

# Why XLSX Chunk Size Behaves Differently

The XLSX input is loaded using:

```python
pd.read_excel(...)
```

before being written to the intermediate CSV.

Therefore, the XLSX file itself is not being chunked during ingestion.

The configured chunk size mainly affects the later stages:

```text
Temporary CSV
      ↓
read_csv(chunksize=...)
      ↓
XLSX writing
```

Consequently, changing the chunk size does not eliminate the memory required to load the original XLSX DataFrame.

This explains why peak RSS remained relatively similar across the tested XLSX chunk sizes.

This is an important architectural distinction:

> **CSV input is genuinely chunked during ingestion; XLSX input is not.**

---

# 📦 Output Format Interpretation

The benchmarks also demonstrate that the requested output format changes the workload.

For the tested workloads:

* **CSV output** is comparatively straightforward and can be written incrementally to disk.
* **XLSX output** requires an additional conversion stage through the temporary CSV and spreadsheet-writing process.

Therefore, output format affects execution time, I/O, and final file size.

In the tested workflows, CSV output generally favored shorter processing time at the cost of larger output files, while XLSX output required more processing work and could produce a more compact spreadsheet representation.

These are **observed V1 workload characteristics**, not universal guarantees for every dataset or filesystem.

---

# 🧩 Input Size and Cell-Content Effects

Input file size, row count, column count, and cell contents all contribute to the amount of work required.

A larger input generally means more data must be parsed and written, increasing potential execution time.

For CSV, chunking controls how much of that data is held in memory at one time.

Cell contents also matter. Large or string-heavy values can require more memory to represent and can increase processing work even when row counts are similar.

Therefore, benchmark results should not be interpreted from file size alone.

A useful model is:

```text
Execution time and memory usage

        ↓

Input size
+ row/column count
+ cell contents
+ input format
+ output format
+ chunk size
+ CPU/system performance
```

The exact effect of each factor depends on the workload and implementation.

---

# 📊 Cross-Dataset Interpretation

Raw throughput should not be used to directly rank the datasets against one another.

For example:

```text
rows/second
```

is affected by row width and data characteristics.

A dataset with string-heavy columns is not equivalent to a dataset with 14 columns of different value types.

Therefore:

* **Rows/sec** is useful when comparing the same workload under different configurations.
* **MB/sec** provides additional context when comparing workloads with different row widths.
* Memory measurements should be interpreted alongside the dataset structure.
* Execution time should be interpreted alongside the CPU configuration and hardware.

---

# 🧠 Benchmark Conclusions

The current benchmarks support several practical conclusions.

## 1. Chunking substantially reduces CSV memory usage

The large CSV benchmark showed that reducing chunk size can dramatically lower peak memory.

For example, the 5M-row chunk configuration reached approximately 1.89 GB peak RSS, while the 1M-row configuration reached approximately 464 MB under the same workload.

This is the clearest performance/resource trade-off established by the benchmark suite.

---

## 2. Larger chunks did not consistently provide faster processing

Increasing chunk size produced much larger memory requirements without a proportional improvement in execution time.

Therefore, there appears to be a diminishing-return region in the tested workloads.

Chunk size should be treated primarily as a memory/performance tuning parameter rather than a setting that simply makes the program faster when increased.

---

## 3. 50,000 is a defensible default

The current default of:

```text
50,000 rows
```

is reasonable for the tested hardware and workloads.

This should not be interpreted as a universal optimal value.

The benchmark instead demonstrates why a moderate chunk size is a practical default: substantially larger chunks can consume considerably more RAM without providing a similarly large throughput benefit.

Users with different memory capacities or workloads may choose a different value.

---

## 4. XLSX remains the major memory limitation

CSV processing can be genuinely chunked.

XLSX input cannot currently follow the same architecture.

Therefore:

```text
CSV
 ↓
chunk
 ↓
process
 ↓
write
```

has better out-of-core behavior than:

```text
XLSX
 ↓
load entire workbook/worksheet
 ↓
write to CSV
```

True streaming XLSX ingestion remains a major future optimization.

---

## 5. Execution speed is hardware-dependent

The benchmarks also demonstrate that execution time is not solely a property of the Concatenator implementation.

CPU performance, thermal conditions, and the general system environment affect how quickly the same workload completes.

The 60% CPU performance cap was therefore part of the benchmark configuration rather than merely an incidental laptop setting.

The measured execution times should be treated as:

> **Reference measurements for the documented hardware and CPU configuration.**

---

# ⚠️ Benchmark Limitations

These benchmarks have several limitations.

### Thermal limitation

The long CSV tests were performed with a 60% CPU performance cap to avoid sustained extreme temperatures.

### Hardware limitation

The results describe the developer's current laptop, not a universal hardware baseline.

### Same-process repetitions

Repeated runs are performed sequentially in the same Python process.

This can cause later OS baselines to differ because memory may be retained or reused by the Python runtime and underlying libraries.

For this reason, Peak RSS is more useful for comparing workload memory than Net RSS across repetitions.

### Limited benchmark count

Only a small number of datasets and chunk sizes were tested.

### No controlled Calamine/OpenPyXL comparison

Calamine was selected based on research, but its performance advantage over other Excel engines has not yet been directly benchmarked in this project.

### No comprehensive failure testing

The current benchmark suite does not extensively test:

* Interrupted processing
* Disk-full conditions
* Permission failures
* Corrupted workbooks
* Exact Excel row-limit boundaries
* Temporary-file cleanup after failure

These remain future test areas.

### No claim of universal optimality

The benchmarks describe behavior observed under specific workloads, software versions, and hardware conditions.

They should not be interpreted as universal performance guarantees.

---

# 🎯 Current Decision

Based on the current evidence:

> **The current disk-backed concatenation architecture is accepted for V1.**

The primary reason is that it successfully avoids the severe memory behavior encountered during early `pd.concat()` experiments.

The benchmarks also show that chunk size can dramatically affect memory consumption while producing relatively small throughput differences in the tested workloads.

Therefore, the current design prioritizes:

```text
Memory safety
     ↓
Data preservation
     ↓
Practical execution
     ↓
Performance optimization
```

rather than maximizing theoretical throughput at the expense of memory.

The benchmark suite is considered sufficient for the V1 release baseline. Future changes to the architecture can use these results as the comparison point rather than requiring the entire benchmark process to be repeated without a code or architectural change.

---

# 🔮 Future Testing

Future optimization passes should investigate:

* Calamine vs OpenPyXL
* True streaming XLSX readers
* XLS support
* Larger and smaller chunk sizes
* Better XLSX writing strategies
* Automatic chunk-size selection
* Parallel processing
* Failure cleanup
* Exact Excel row-limit behavior
* More comprehensive schema validation
* Additional spreadsheet formats
* Fresh-process benchmark repetitions when cleaner baseline isolation is required

The current benchmarks provide a baseline for those future experiments.

---

# ✅ Status

**Accepted — V1 functional testing and initial performance benchmarking complete.**

The Concatenator successfully handles the six primary CSV/XLSX format combinations tested.

The current architecture has known limitations, particularly around XLSX ingestion and schema/dtype handling, but these limitations are explicitly documented rather than hidden.

The benchmark results establish a practical V1 baseline for memory behavior, throughput, output-format trade-offs, chunk-size behavior, and hardware-dependent execution time.

The next optimization cycle can therefore build on a measured baseline rather than redesigning the system blindly.
