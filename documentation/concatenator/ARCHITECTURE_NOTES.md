# 🏗️ Architecture Notes

This document records the architectural decisions behind the **Spreadsheet Concatenator**, including the reasoning, trade-offs, experimentally observed limitations, benchmark findings, and future improvements.

The purpose of this document is not to present the architecture as universally optimal.

Instead, it records **why the current implementation exists in its current form** and what was learned during development.

---

# Project Context

The Spreadsheet Concatenator is part of the broader **CleanSheet** project.

The original goal was to build a personal spreadsheet utility capable of combining CSV, XLSX, and originally XLS files.

The project is intended primarily for the developer's own spreadsheet-related workflows, while remaining useful enough that other users could potentially use it as well.

The broader CleanSheet project is intended to eventually combine:

* Data quality checking
* Spreadsheet concatenation
* Spreadsheet cleaning

The Concatenator is specifically focused on combining datasets while avoiding unnecessary modification of their values.

---

# Guiding Philosophy: Make It Work, Then Optimize

The primary development philosophy is:

> **Make it work first. Optimize later.**

This was particularly important because the project was being developed alongside college and other responsibilities.

The goal was therefore not to design the perfect spreadsheet-processing architecture before writing the first implementation.

Instead, the architecture evolved through:

```text
Build
  ↓
Test
  ↓
Encounter limitation
  ↓
Investigate
  ↓
Modify architecture
  ↓
Benchmark
  ↓
Document
```

This process directly influenced the current design.

---

# 1. Why Vertical Concatenation Instead of Automatic Merging?

### Choice

The Concatenator performs vertical row appending.

It does not currently attempt to intelligently merge arbitrary spreadsheet schemas.

### Rationale

The original goal was simply to combine spreadsheet files into one output file.

During development, attempts to combine files with different columns produced malformed or unexpected results.

Automatically deciding how different schemas should be combined is considerably more complicated than simply appending rows.

For example:

```text
File A:
Name | Age | City

File B:
Name | Salary | Department
```

There are several possible interpretations of what the output should mean.

Automatically choosing one could produce incorrect data.

Therefore, V1 requires compatible columns instead.

### Trade-off

The implementation is significantly simpler and safer for the current scope.

However, files that could theoretically be aligned through a more sophisticated schema-mapping system cannot currently be concatenated.

### Future Improvement

Possible future functionality:

* Column mapping
* Schema alignment
* Optional column reordering
* Missing-column handling
* Explicit user confirmation before schema changes

---

# 2. Exact Column Matching

### Choice

Column names and order must match exactly.

The comparison currently uses the equivalent of:

```python
list(df.columns) == expected_columns
```

### Rationale

This was introduced after incompatible inputs caused malformed output.

The design intentionally favors:

> **Fail explicitly rather than silently create a questionable dataset.**

### Trade-off

The implementation does not currently support harmless differences such as:

```text
Name
```

versus:

```text
name
```

or different column ordering.

### Architectural Limitation

Column compatibility is currently stricter than many spreadsheet tools.

Schema normalization is intentionally deferred.

---

# 3. CSV Chunked Processing

### Choice

CSV input is processed using:

```python
pd.read_csv(filepath, chunksize=chunksize)
```

rather than loading the entire CSV into one DataFrame.

### Rationale

The primary reason was memory usage.

The project is intended to handle large spreadsheet exports, including multi-gigabyte CSV files, on ordinary hardware.

Loading an entire multi-gigabyte CSV into memory would create an unnecessary dependency between:

```text
Dataset size
    ↓
RAM requirement
```

Chunking changes the processing model to:

```text
Large file
   │
   ├── chunk
   ├── chunk
   ├── chunk
   └── chunk
        │
        ▼
      disk
```

Only the current chunk needs to be processed by the CSV path at one time.

### Trade-off

Chunking introduces additional iteration and I/O overhead.

The benchmark results showed that chunk size is a meaningful memory/performance tuning parameter, but increasing it did not consistently produce proportional throughput improvements.

For example, the large `5m Sales Records.csv × 2` workload reached approximately **1.89 GB peak process RSS** with a 5,000,000-row chunk, while the same workload at a 1,000,000-row chunk reached approximately **464 MB peak process RSS**. Throughput remained in a similar range in those two tests.

This demonstrates the main architectural trade-off:

> **Larger chunks can substantially increase memory requirements without guaranteeing a comparable increase in throughput.**

### Architectural Interpretation

Chunking should therefore be treated as a mechanism for **controlling memory pressure**, not simply as a way to make processing faster.

The appropriate chunk size depends on the workload and available hardware.

---

# 4. Why XLSX Is Not Truly Streamed

### Choice

XLSX input is currently loaded into memory:

```python
df = pd.read_excel(filepath, engine="calamine")
```

and then written into the intermediate CSV.

### Rationale

The current implementation could not apply the same `chunksize`-based input mechanism used by `read_csv()` to XLSX ingestion.

The project therefore needed another way to bring XLSX data into the disk-backed concatenation pipeline.

The chosen approach was:

```text
XLSX
 ↓
DataFrame
 ↓
CSV
```

Once converted to CSV, the data can participate in the same chunked processing pipeline as CSV inputs.

### Important Architectural Limitation

This does **not** mean XLSX ingestion is out-of-core.

The XLSX file itself still requires enough memory to create its DataFrame.

Therefore:

> **CSV ingestion is chunked; XLSX ingestion is not.**

This distinction is important when interpreting the benchmark results. Larger XLSX inputs can place more memory pressure on the process before the disk-backed CSV stage can reduce the dependence on the size of the combined dataset.

### Why This Was Still Better Than `pd.concat()`

The alternative tested during development was effectively:

```text
XLSX A → DataFrame
XLSX B → DataFrame
XLSX C → DataFrame
       ↓
   pd.concat()
       ↓
   output
```

This caused severe memory pressure and, in larger tests, triggered Linux's OOM killer and system freezes.

The current design instead becomes:

```text
XLSX A ──┐
XLSX B ──┼──> temporary/output CSV
XLSX C ──┘
             ↓
       chunked processing
```

The important improvement is that the application does not need to maintain the entire **combined dataset** as a collection of DataFrames.

---

# 5. Why Not `pd.concat()`?

### Choice

The Concatenator does not build the final dataset using `pd.concat()`.

### Rationale

This decision came directly from experimentation.

The initial approach attempted to load data into DataFrames and concatenate them.

The memory behavior was poor enough that even relatively modest spreadsheet combinations could produce unexpectedly high RAM usage.

Larger combinations could trigger:

```text
Linux OOM killer
      ↓
process termination / system freeze
```

The application therefore moved toward disk-backed incremental writing.

### Trade-off

The disk-backed architecture can involve more I/O and intermediate files.

However, this trade-off was accepted because the primary problem being solved was **memory scalability**.

A theoretically elegant in-memory DataFrame workflow is not useful if the machine runs out of memory before the operation completes.

---

# 6. Intermediate CSV for XLSX Output

### Choice

When the requested output format is XLSX, the program first produces a temporary CSV.

```text
Input
 ↓
stream_to_csv()
 ↓
temporary CSV
 ↓
pd.read_csv(..., chunksize=...)
 ↓
XlsxWriter
 ↓
final XLSX
```

### Rationale

This allows the same concatenation engine to process CSV and XLSX inputs before the final format conversion.

It also avoids having to construct one enormous final DataFrame just to produce an XLSX file.

The temporary CSV effectively acts as a **disk-backed intermediate representation**.

### Trade-off

The dataset is written to disk and then read again.

This increases I/O and therefore can increase total execution time.

The benchmark results are consistent with this trade-off: in the tested workloads, CSV output completed faster, while XLSX output required additional processing and therefore took longer.

However, the XLSX output path can produce a smaller final file than its CSV counterpart for the same tabular data.

### Why Not Just `pd.concat()` Then `to_excel()`?

That approach was already problematic because `pd.concat()` required maintaining the combined dataset in memory.

The intermediate CSV approach trades some I/O for much lower dependence on the total merged dataset size.

---

# 7. Temporary File Cleanup

### Choice

The temporary CSV is deleted after successful XLSX generation.

### Rationale

The temporary CSV is an implementation detail and should not remain after successful processing.

### Known Limitation

Cleanup is currently not guaranteed if the XLSX conversion fails or the process is interrupted.

For example:

```text
Create temp CSV
       ↓
Begin XLSX conversion
       ↓
Failure / cancellation
       ↓
Temporary CSV may remain
```

This is an acknowledged V1 limitation.

### Future Improvement

Temporary-file handling should eventually use stronger cleanup guarantees, such as a `try/finally` strategy, so temporary resources are removed even when processing fails.

---

# 8. XlsxWriter `constant_memory=True`

### Initial Approach

The project originally experimented with XlsxWriter's:

```python
constant_memory=True
```

option for XLSX generation.

The intention was to reduce memory usage during large XLSX writes.

### Observed Problem

The project found that combining this mode with Pandas:

```python
chunk.to_excel(...)
```

could result in incomplete or missing cell values without necessarily producing an obvious Python exception.

Because data correctness is more important than the memory optimization, the option was removed.

The current implementation therefore uses:

```python
pd.ExcelWriter(
    output_path,
    engine="xlsxwriter"
)
```

without `constant_memory=True`.

### Important Qualification

This should **not** be interpreted as:

> "`constant_memory=True` is universally incompatible with Pandas."

The observation is specific to the way this project combines:

* Pandas DataFrames
* `DataFrame.to_excel()`
* repeated chunk writes
* XlsxWriter constant-memory mode

The safer choice for the current implementation was therefore to remove the optimization.

### Architectural Trade-off

The project gives up some potential memory optimization during XLSX generation in exchange for more reliable output.

This is an example of:

> **Correctness before optimization.**

---

# 9. Why Calamine?

### Choice

XLSX files are read with:

```python
pd.read_excel(filepath, engine="calamine")
```

### Rationale

The decision was based on research rather than a direct benchmark against every available Excel engine.

Calamine was selected because it is a Rust-based spreadsheet parser and was researched as a potentially efficient alternative to Python-based Excel readers.

Lower memory use and faster spreadsheet reading were part of the motivation.

### Evidence Level

This is currently a **research-informed architectural choice**, not a project-proven benchmark result.

The project has not performed a controlled Calamine vs OpenPyXL benchmark using the same datasets and environment.

### Future Improvement

A future optimization pass should benchmark the available XLSX engines under controlled conditions.

---

# 10. XLS Support Was Removed

### Original Plan

The original project intended to support:

```text
CSV
XLSX
XLS
```

### Problem

The selected XLSX output library, XlsxWriter, does not write legacy `.xls` files.

This was discovered after much of the Concatenator had already been implemented.

### Decision

Instead of rebuilding the output architecture around another library, XLS support was removed from V1.

### Rationale

The project needed to reach a functional release rather than indefinitely expanding scope.

Supporting XLS properly could require changes to:

* Input handling
* Output handling
* Format-specific libraries
* Validation
* Testing
* Potentially the overall architecture

The limitation was therefore explicitly accepted.

### Future Direction

XLS support remains on the future-improvement list because compatibility with older spreadsheet files is useful for real-world spreadsheet workflows.

---

# 11. Excel Row Limit Handling

### Choice

The XLSX output path checks the Excel worksheet row limit.

The implementation uses:

```text
1,048,576 rows
```

as the maximum worksheet size.

### Rationale

The limit was researched before implementation.

The program should not silently attempt to create an XLSX workbook that exceeds the format's worksheet capacity.

The current behavior is therefore defensive:

```text
Dataset exceeds Excel capacity
          ↓
Warn user
          ↓
Limit XLSX output
          ↓
Recommend CSV for larger data
```

### Testing Status

This behavior was implemented defensively but has not been extensively stress-tested at the exact Excel boundary.

---

# 12. Chunk Size

### Choice

The default chunk size is:

```text
50,000 rows
```

### Rationale

The initial value was inherited partly from the Quality Checker implementation and chosen as a practical balance between memory usage and processing time.

It was never intended to represent a universal optimum.

### Benchmark Findings

The newer benchmark suite reinforced that chunk size is primarily a **memory/performance tuning parameter** rather than a guaranteed speed control.

For the `vehicles.csv` workload, the tested values showed approximately:

| Chunk Size | Peak RSS | Runtime |
| ----------: | -------: | ------: |
| 50,000 | ~1.24 GB | ~178.5 s |
| 100,000 | ~2.08 GB | ~181.3 s |
| 200,000 | ~3.78 GB | ~181.3 s |

The exact runtime values should not be treated as universal performance guarantees. The important observation is that **memory consumption increased substantially while throughput remained broadly similar** for this workload.

The larger `5m Sales Records.csv × 2` workload provided another useful comparison:

| Chunk Size | Peak Process RSS | Throughput |
| ----------: | ----------------: | ---------: |
| 1,000,000 | ~464 MB | ~13.2k rows/s |
| 5,000,000 | ~1.89 GB | ~13.2k rows/s |

This demonstrates that a much larger chunk can consume several times more memory without producing a comparable throughput improvement.

### Architectural Interpretation

The benchmark results suggest that increasing chunk size beyond a certain point can produce **diminishing performance returns** while continuing to raise peak memory usage.

The chunk size is therefore better understood as a **memory/performance tuning parameter**. Users with limited RAM can reduce chunk size to lower peak memory pressure, while larger chunk sizes may be useful when additional memory is available and a workload benefits from larger batches.

The benchmark does **not** establish that a particular chunk size is universally optimal.

---

# 13. Benchmark CPU Cap

### Choice

The benchmark suite was performed under a CPU performance limit of approximately **60%** on the developer's test laptop.

### Rationale

Higher CPU performance limits caused sustained temperatures approaching the laptop's thermal ceiling during long-running workloads.

Observed operating ranges included approximately:

```text
60% CPU limit → ~78–92 °C
85% CPU limit → ~98–100 °C
```

The 60% setting was therefore selected as a practical thermal-conscious configuration for repeated benchmark runs.

This was not intended to measure maximum possible hardware performance.

### Benchmark Interpretation

CPU performance is one variable affecting execution time.

The measured execution time is therefore influenced by both the Concatenator and the environment in which it runs:

```text
Execution time
    ↓
Application implementation
+ input workload
+ input/output format
+ chunk size
+ CPU performance
+ system/runtime conditions
```

The 60% cap provides a documented and repeatable test condition, but absolute execution times should not be treated as universal values for other machines.

### Why Include the CPU Variable?

The `100mb.xlsx` workload was also useful for observing the relationship between CPU performance and execution time because it completed relatively quickly compared with the largest CSV workloads.

The benchmark therefore treats CPU performance as part of the experimental environment rather than attributing all execution-time differences to the Concatenator itself.

### Important Distinction

The CPU performance cap is separate from the benchmark's measured process CPU utilization.

A process reporting approximately 100% CPU does not mean that the laptop's CPU was operating at unrestricted maximum performance.

---

# 14. Benchmark Dataset Selection

The datasets were intentionally selected to stress different characteristics.

### Large CSV

`5m Sales Records.csv` was used twice.

Approximate combined size:

```text
1.19 GB
```

Total rows:

```text
10,000,000
```

Columns:

```text
14
```

This workload tests large CSV processing and makes the effect of chunk size on memory especially visible.

### String-Heavy CSV

`vehicles.csv` was used twice.

Approximate combined size:

```text
2.762 GB
```

Rows:

```text
853,760
```

Columns:

```text
26
```

This workload was selected because its data characteristics create a substantially different memory/processing profile.

### XLSX

`100mb.xlsx` was used three times.

Approximate combined size:

```text
302 MB
```

Rows:

```text
81,000
```

Columns:

```text
8
```

This workload was selected to exercise XLSX ingestion and XLSX output behavior.

### Why Different Workloads Matter

The benchmark results support treating input size, data characteristics, and output format as independent workload variables rather than assuming that file size alone determines performance.

Larger or more substantial cell values can increase the amount of data that must be represented, parsed, copied, and written, which can increase both processing time and memory pressure.

The exact effect depends on the format and processing path. In particular, CSV can reduce the relationship between total dataset size and peak memory through chunking, while XLSX input is currently loaded into memory as a DataFrame.

### Output Format as a Workload Variable

The requested output format also affects resource usage and execution time.

In the tested workloads:

| Output | Observed behavior |
| --- | --- |
| CSV | Faster processing and larger resulting files |
| XLSX | Longer processing and smaller resulting files |

These are **observed V1 benchmark results**, not universal guarantees for every dataset or environment.

The XLSX path performs additional work because it first creates an intermediate CSV and then converts that representation into an XLSX workbook.

### Purpose

The goal was not to create a statistically representative benchmark suite.

The goal was to **push the application toward difficult workloads**, expose architectural trade-offs, and identify where resource usage or execution time becomes significant.

---

# 15. Data Type Preservation

### Choice

The Concatenator does not automatically normalize column datatypes across input files.

### Rationale

The feature's responsibility is concatenation, not data cleaning.

Automatically converting every numeric-looking value could damage meaningful identifiers.

For example:

```text
00001234
```

could become:

```text
1234
```

which changes the original value.

The project therefore prefers:

> **Preserve values rather than make assumptions about their meaning.**

### Known Consequence

Different input formats can result in different Pandas representations of logically similar values.

This can produce dtype or value-representation differences when CSV and XLSX files are mixed.

The behavior is currently accepted as an intentional consequence of the preservation philosophy.

---

# 16. Duplicate File Prevention

### Choice

The GUI prevents the same resolved file path from being added multiple times.

### Rationale

This is primarily a user-experience feature.

Accidentally selecting the same file twice should not silently result in duplicated data.

The processing core does not attempt to determine whether two separate files contain identical data.

---

# 17. GUI and Processing Separation

### Choice

The processing layer is separated from the GUI layer.

The core functions are:

```python
stream_to_csv()
concat_files()
```

while:

```python
build_concatenator_tab()
```

handles the interface.

### Rationale

This separation makes the processing logic easier to reason about and test independently from Tkinter.

It also provides a possible foundation for future architectural restructuring.

An OOP-based design may be considered later, but no class architecture has been committed to yet.

---

# 18. Background Threading

### Choice

Concatenation runs in a background thread.

### Rationale

Large spreadsheet operations can take minutes.

Running them directly on Tkinter's main thread causes the interface to freeze.

The GUI therefore remains responsive while processing occurs separately.

### Trade-off

Threading introduces additional coordination complexity.

However, responsiveness is important for a desktop application performing long-running operations.

---

# 19. Indeterminate Progress

### Choice

The current progress indicator is indeterminate.

### Rationale

The exact amount of work depends on:

* Number of files
* File sizes
* Number of CSV chunks
* XLSX conversion
* Output format
* Excel row-limit behavior

The implementation does not currently calculate a reliable total amount of work.

Rather than display a potentially misleading percentage, the GUI uses an indeterminate progress indicator.

### Future Improvement

A future version could estimate progress based on bytes processed, rows processed, or another measurable unit.

---

# 20. Error Handling

### Choice

The processing layer raises errors while the GUI handles how those errors are presented to the user.

### Rationale

This keeps the processing functions from becoming tightly coupled to the user interface.

For example:

```text
Processing layer
      ↓
raise ValueError(...)
      ↓
GUI catches error
      ↓
messagebox.showerror(...)
```

This separation allows the core processing code to remain usable independently of Tkinter.

---

# 21. What Was Intentionally Not Built in V1?

The following features were deliberately left outside the first release:

* XLS support
* Multiple worksheet processing
* Automatic schema normalization
* Column reordering
* Automatic datatype conversion
* Missing-value normalization
* Parallel processing
* True streaming XLSX input
* Percentage progress
* Resume support
* Compression
* Database-backed processing
* Cloud storage

The absence of these features should not be interpreted as proof that they are unnecessary.

They were excluded primarily to keep the project achievable and prevent scope from expanding indefinitely.

---

# 22. Known Architectural Limitations

The most important current limitations are:

### XLSX input is not out-of-core

The complete XLSX worksheet is loaded into memory.

### Temporary-file cleanup is incomplete

Interrupted or failed XLSX conversions can leave the temporary CSV.

### Schema matching is strict

Column names and ordering must match exactly.

### Datatype normalization is absent

Mixed-format datasets can produce representation differences.

### XLS is unsupported

The current architecture does not write legacy `.xls`.

### XLSX writing is not using `constant_memory=True`

The optimization was removed because of incorrect/incomplete output observed with the project's Pandas chunk-writing approach.

### Progress is indeterminate

The GUI does not provide a precise percentage.

### Benchmark results are hardware- and workload-dependent

The recorded execution times and memory measurements describe the tested implementation under the documented hardware and CPU-performance conditions.

They should not be interpreted as universal performance guarantees for every machine, operating system, dataset, or CPU configuration.

### Repeated benchmark runs share one Python process

The benchmark repetitions are executed sequentially in the same Python process. Consequently, the OS RSS baseline can increase between runs because the Python runtime and underlying libraries may retain or reuse memory.

For this reason, **peak process RSS** is the primary memory metric, while baseline and net RSS are treated as diagnostic measurements rather than direct standalone measures of workload memory use.

---

# 23. Future Architectural Direction

Future optimization can focus on several areas.

## True XLSX Streaming

Investigate libraries or APIs that can process XLSX worksheets incrementally rather than loading the entire worksheet into memory.

This is likely the largest architectural improvement for memory scalability.

## XLS Support

Investigate appropriate libraries or conversion strategies for legacy `.xls`.

## Better Cleanup

Guarantee temporary-file cleanup during:

* Success
* Failure
* User cancellation
* Unexpected exceptions

## Better Schema Handling

Potentially introduce explicit schema mapping rather than automatic guessing.

## Parallel Processing

Explore whether independent file parsing or conversion can safely be parallelized without creating another memory bottleneck.

## Output Optimization

Investigate more efficient CSV and XLSX writing strategies.

## Better Validation

Expand the test suite to include:

* Mismatched columns
* Unsupported extensions
* Empty files
* One-file input
* Invalid destination folders
* Blank filenames
* Duplicate files
* Excel row-limit boundaries
* Temporary-file cleanup
* Interrupted processing

---

# 24. Final Design Position

The current architecture is intentionally a compromise.

It does **not** provide true streaming for every spreadsheet format.

It does **not** automatically repair schemas.

It does **not** normalize datatypes.

It does **not** maximize CPU utilization at all costs.

Instead, it prioritizes:

1. Correct row concatenation
2. Avoiding the severe memory behavior observed with `pd.concat()`
3. Practical desktop usability
4. Data preservation
5. Clear failure when schemas are incompatible
6. Incremental improvement through measurement
7. Predictable resource behavior under the documented benchmark conditions

The benchmark results added another architectural lesson: **performance is a multi-variable trade-off rather than a single speed number**.

Input size, data characteristics, chunk size, output format, CPU performance, and the processing architecture all contribute to observed execution time and memory usage.

The current implementation therefore does not claim a universal "fastest" or "lowest-memory" configuration. Instead, V1 documents the behavior of the selected architecture under representative workloads and uses those measurements to justify design decisions such as chunked CSV processing and the disk-backed XLSX pipeline.

The most important lesson from the architecture is that a theoretically simple approach is not necessarily practical at scale.

The project originally attempted a more direct in-memory approach.

Real testing demonstrated that it could trigger OOM conditions.

The resulting disk-backed architecture is therefore not simply a stylistic preference.

It is a response to an experimentally observed limitation.

> **Build it. Measure it. Learn where it breaks. Then optimize it.**
