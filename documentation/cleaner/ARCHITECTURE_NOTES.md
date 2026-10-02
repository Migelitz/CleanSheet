# CleanSheet Architecture Notes

This document records the reasoning behind the architecture of CleanSheet, including the problems encountered during development, the tradeoffs made, and areas where the current implementation is based on practical assumptions rather than measured benchmarks.

The goal is not to present every decision as perfectly planned from the beginning. CleanSheet evolved through experimentation, problems encountered during development, research, and iterative changes.

## 1. Overall Goal

The original goal of the cleaner was simple:

> Build a GUI that allows spreadsheet data to be cleaned without repeatedly writing Pandas/Python code.

Writing a new Pandas script every time a spreadsheet needs slightly different cleaning operations is repetitive. A graphical interface allows the cleaning logic to become reusable.

Instead of:

```text
New spreadsheet
    ↓
Write Pandas script
    ↓
Run script
    ↓
Modify script for another spreadsheet
    ↓
Repeat
```

CleanSheet aims for:

```text
New spreadsheet
    ↓
Select file
    ↓
Configure cleaning operations
    ↓
Run
    ↓
Cleaned spreadsheet
```

The primary user for the project is myself, although the architecture is intended to demonstrate practical Python automation and data-processing skills as a portfolio project.

---

# 2. Architecture Overview

The cleaner can be viewed as three main layers:

```text
┌─────────────────────────────┐
│          GUI Layer          │
│                             │
│ File selection              │
│ Cleaning options            │
│ Column configuration        │
│ Progress / status feedback  │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│      Cleaning Engine        │
│                             │
│ clean_dataframe()           │
│ Text cleaning               │
│ Column transformations      │
│ Missing-value handling      │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│       Export Pipeline       │
│                             │
│ CSV chunk processing        │
│ Duplicate handling          │
│ XLS/XLSX processing         │
│ Output generation           │
└─────────────────────────────┘
```

The important separation is between `clean_dataframe()` and the file-processing/export logic.

`clean_dataframe()` is responsible for transforming a DataFrame.

The surrounding processing code is responsible for deciding how data is loaded, how chunks are handled, how duplicates are tracked, and how the result is exported.

This separation makes the actual cleaning operations reusable independently of the GUI.

---

# 3. Header-Only File Loading

## Problem

An earlier implementation loaded the complete spreadsheet when the user selected a file.

This became a problem with larger datasets. During development, I tested a dataset of approximately **426,000 rows and 26 columns**, and loading the data for the purpose of configuring the GUI caused the interface to become unresponsive and eventually crash.

The GUI only needed the column names at this stage.

Loading hundreds of thousands of rows simply to populate column selectors was unnecessary.

## Decision

The cleaner now reads only the headers when a file is selected.

For CSV:

```python
pd.read_csv(filepath, nrows=0)
```

For Excel:

```python
pd.read_excel(filepath, engine="calamine", nrows=0)
```

The application therefore stores information such as:

```text
file path
column names
```

rather than immediately storing the complete dataset.

## Reasoning

The primary goals were:

1. Reduce unnecessary memory usage.
2. Keep the GUI responsive during file selection.
3. Allow column selectors to be populated without loading the complete dataset.

This reflects an important design principle used throughout the cleaner:

> Do not load data until the application actually needs the data.

---

# 4. Why CSV Uses Chunk Processing

CSV → CSV processing uses Pandas chunking:

```python
pd.read_csv(file, chunksize=50_000)
```

Instead of:

```text
Entire CSV
    ↓
Entire DataFrame
    ↓
Clean
    ↓
Export
```

the cleaner uses:

```text
CSV
 ↓
Chunk 1
 ↓
Clean
 ↓
Export
 ↓
Chunk 2
 ↓
Clean
 ↓
Export
 ↓
...
```

## Why 50,000 Rows?

The value of 50,000 was chosen as a practical starting point.

There is no rigorous benchmark proving that 50,000 is the optimal chunk size for every machine or dataset.

The choice was influenced by the same general approach used elsewhere in the project: choose a reasonable chunk size that the development machine can handle, then optimize further if future testing demonstrates that another size is better.

Therefore, the current value should be considered a configurable engineering assumption rather than a universally optimal number.

A future performance study could compare different chunk sizes against:

* execution time
* peak memory
* CPU usage
* dataset structure
* transformation complexity

---

# 5. Why Excel Is Different

Originally, the intention was for XLS and XLSX files to receive chunked processing as well.

During development, I discovered that the Excel workflow could not simply be treated like CSV chunking.

Excel is a more complex document format than plain delimited text. The current Pandas-based implementation therefore loads XLS/XLSX data into a complete DataFrame instead of attempting to force the CSV chunking approach onto it.

This is currently accepted as a **v1.0.0 limitation**.

The design therefore deliberately prioritizes a reliable chunked path for CSV rather than pretending that every spreadsheet format has identical processing characteristics.

Future versions may investigate alternative Excel-reading strategies if large Excel files become an important requirement.

---

# 6. Per-Column Transformations

Transformations are selected on a column-by-column basis.

For example:

```text
name       → Split Human Names
email      → Extract Email
phone      → Numbers Only
currency   → Clean Currency
```

## Why Not Transform Every Column?

Applying every transformation globally would create several problems.

First, different columns contain different kinds of data.

For example:

```text
name
email
phone
currency
date
description
```

A transformation that makes sense for `phone` may completely corrupt a `description` column.

Second, applying transformations to columns that do not need them introduces unnecessary computation.

The per-column model therefore provides:

* More control
* Lower unnecessary processing
* Reduced risk of unintended modifications
* A more practical GUI for heterogeneous spreadsheets

This was also one of the reasons the column selectors became an important part of the interface.

---

# 7. Choosing the Transformations

The transformation set evolved partly from wanting the cleaner to provide more useful functionality rather than only basic operations.

Simple operations such as trimming whitespace and changing case are useful, but the cleaner became more interesting when it could handle common structured-data problems.

The resulting transformations include:

* Number extraction
* Currency cleaning
* Email extraction
* URL extraction
* Email anonymization
* Number anonymization
* Human-name splitting
* Date normalization

Some of these were inspired by research and suggestions for additional spreadsheet-cleaning operations.

The goal was not to create a universal data-cleaning algorithm. Instead, the goal was to provide reusable operations that could reasonably appear in real spreadsheet-processing tasks.

---

# 8. Duplicate Removal

Duplicate removal was added because removing duplicate rows is a common spreadsheet-cleaning operation.

The initial reasoning was straightforward:

> If duplicate removal is enabled, remove duplicate rows.

The current implementation uses exact duplicate matching rather than fuzzy matching.

For example:

```text
Alice | alice@example.com | 100
Alice | alice@example.com | 100
```

is considered a duplicate.

But:

```text
Alice Smith | alice@example.com
Alice S.    | alice@example.com
```

is not automatically considered the same person.

## Why Exact Duplicates?

Fuzzy duplicate detection introduces significantly more ambiguity.

Two similar rows are not necessarily duplicates. Automatically deciding that they represent the same record can remove legitimate data.

For v1.0.0, exact duplicate removal is therefore a simpler and more predictable behavior.

---

# 9. Cross-Chunk Duplicate Detection

Chunking introduces a specific duplicate problem.

Suppose a dataset is divided like this:

```text
Chunk 1
├── Row A
├── Row B
└── Row C

Chunk 2
├── Row D
├── Row A
└── Row E
```

`drop_duplicates()` operating independently on each chunk can remove duplicates **inside** each chunk, but it cannot know that `Row A` already existed in a previous chunk.

The cleaner therefore maintains a global set of previously encountered row hashes.

Conceptually:

```text
Read chunk
     ↓
Clean chunk
     ↓
Remove duplicates inside chunk
     ↓
Hash rows
     ↓
Check hashes against seen_hashes
     ↓
Keep unseen rows
     ↓
Add new hashes to seen_hashes
     ↓
Write chunk
```

This allows duplicate state to persist between chunks without retaining every previous row as a DataFrame.

## Why Hashes?

The technique was discovered through research and exploration of approaches to chunked duplicate detection.

The important problem was:

> How can previously encountered rows be remembered without retaining the entire processed dataset?

A hash provides a compact representation that can be stored in a set.

The current implementation uses:

```python
pd.util.hash_pandas_object(...)
```

followed by a set of previously encountered hashes.

This approach was selected based on the expected properties of hashing, but it has **not yet been comprehensively benchmarked** against alternative duplicate-tracking strategies for CleanSheet's actual workloads.

Hashing also has a theoretical collision possibility. It should therefore not be described as mathematically collision-free.

Future testing should investigate:

* Memory overhead of `seen_hashes`
* Processing overhead of hashing
* Effect of increasing duplicate rates
* Larger datasets
* Alternative duplicate-tracking approaches

---

# 10. Memory Was the Primary Optimization Target

The most important performance consideration during development was memory usage.

The development machine has:

* 8 GB RAM
* Intel Core i5-1035G1
* Linux Mint 22.3

Because the application was being developed on a relatively constrained machine, memory usage was not an abstract concern.

It directly affected whether the application remained usable.

The design therefore prioritized:

```text
Memory usage
    ↓
GUI responsiveness
    ↓
Ability to process larger files
```

rather than initially optimizing purely for maximum throughput.

Now that the basic memory-oriented architecture is working, future development can place more emphasis on balancing:

* memory
* speed
* CPU usage
* responsiveness
* maintainability

---

# 11. Background Threading

Even with chunking, spreadsheet processing can take significant time.

During development, the GUI would freeze when cleaning operations were performed directly in the Tkinter execution path.

The solution was to move the processing work into a background thread.

Conceptually:

```text
Main Tkinter thread
        │
        ├── GUI
        ├── User interaction
        └── Status updates
       
Background worker
        │
        ├── Read data
        ├── Clean data
        ├── Deduplicate
        └── Export
```

The goal is simple:

> The application should remain responsive while processing occurs in the background.

The progress indicator is intentionally indeterminate because the current implementation does not calculate a reliable percentage for every processing path.

It therefore communicates that work is occurring without pretending to know an exact completion percentage.

---

# 12. Tkinter Thread Safety

Tkinter widgets should not be directly manipulated from an arbitrary worker thread.

The cleaner therefore captures the necessary GUI state before starting the worker rather than having the worker repeatedly read Tkinter variables.

This design came from research and guidance around Tkinter's thread-safety limitations rather than from personally encountering a thread-related widget failure.

GUI updates are then scheduled back onto the Tkinter event loop using mechanisms such as:

```python
parent_frame.after(0, callback)
```

This keeps GUI operations in the GUI thread while allowing the expensive processing work to occur separately.

---

# 13. Current Architectural Tradeoffs

The current design makes several deliberate tradeoffs.

| Decision                             | Benefit                                       | Tradeoff                                            |
| ------------------------------------ | --------------------------------------------- | --------------------------------------------------- |
| Header-only file loading             | Lower memory use during configuration         | Data is not loaded until processing                 |
| CSV chunking                         | Better scalability for large CSV files        | More complex processing pipeline                    |
| 50k chunk size                       | Practical starting point for current hardware | Not proven optimal                                  |
| Hash-based cross-chunk deduplication | Avoids retaining previous DataFrames          | Hash storage and computation introduce overhead     |
| Per-column transformations           | Prevents unnecessary/unwanted transformations | Requires more GUI configuration                     |
| Background worker                    | Keeps GUI responsive                          | Adds threading complexity                           |
| Full-memory Excel processing         | Simpler current Excel pipeline                | Large XLS/XLSX files can require substantial memory |
| Exact duplicate matching             | Predictable behavior                          | Does not identify fuzzy/near duplicates             |

---

# 14. What Is Deliberately Out of Scope for v1.0.0?

The current cleaner does not attempt to solve every spreadsheet-processing problem.

The following are currently outside the v1.0.0 scope:

* Batch processing multiple files in the cleaner tab
* Chunked XLS/XLSX processing
* Fuzzy duplicate detection
* Automatic column-type inference
* Undo/history
* Cloud spreadsheet integration
* Automatic detection of every possible data-quality issue
* Guaranteed correct interpretation of arbitrary messy data
* Comprehensive automated GUI testing

These boundaries keep the current implementation manageable while leaving clear areas for future development.

---

# 15. Architecture Evolution

CleanSheet's current architecture was not designed perfectly from the beginning.

It evolved from actual problems encountered during development.

The progression was approximately:

```text
Initial implementation
        ↓
Load complete spreadsheet
        ↓
Large datasets cause GUI freezing / crashes
        ↓
Read only headers during file selection
        ↓
Need to reduce processing memory
        ↓
Introduce CSV chunking
        ↓
Chunk-local duplicate removal is insufficient
        ↓
Introduce cross-chunk hash tracking
        ↓
Processing still blocks GUI
        ↓
Move processing into worker thread
        ↓
Use Tkinter-safe callbacks for GUI updates
```

This evolution is an important part of the project's architecture.

The design was shaped by the practical constraints of the machine, the behavior of larger datasets, and the requirements of the intended workflow.

---

# 16. Future Architecture Work

Future improvements should be driven by measurements rather than assumptions.

Potential areas include:

1. Benchmarking different CSV chunk sizes.
2. Benchmarking cross-chunk duplicate handling at different duplicate rates.
3. Measuring the memory overhead of `seen_hashes`.
4. Comparing alternative duplicate-tracking strategies.
5. Investigating scalable XLS/XLSX processing.
6. Improving throughput after the memory architecture is sufficiently stable.
7. Expanding automated GUI testing.
8. Testing significantly larger datasets.
9. Evaluating whether the current processing order is optimal for different workloads.

The current implementation should therefore be viewed as a practical **v1.0.0 architecture**, not the final architecture of CleanSheet.
