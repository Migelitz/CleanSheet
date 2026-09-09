# Architecture Notes & Design Decisions

This document records the architectural decisions behind the CleanSheet quality-checking engine (`quality_checker.py`), including the reasoning behind the current implementation, known trade-offs, experimentally observed limitations, and areas identified for future improvement.

The quality checker is one feature of CleanSheet, a desktop spreadsheet-cleaning application. It was developed primarily as a personal project to explore practical data-quality analysis on consumer hardware while keeping the implementation understandable, testable, and easy to evolve.

This document intentionally focuses on **engineering decisions and architectural trade-offs** rather than repeating the detailed accuracy results, benchmark tables, or troubleshooting procedures documented elsewhere.

---

## 1\. Project Context

CleanSheet is a desktop GUI application intended to provide spreadsheet-cleaning and data-quality functionality without requiring users to work directly with a data-processing framework.

The quality checker is designed to inspect CSV and Excel datasets and produce a structured audit report containing:

- Dataset geometry and column structure.
- Missing-value statistics.
- Sentinel-value detection.
- Numeric ranges and summary statistics.
- Duplicate-row counts.
- Type-drift detection.
- Low-cardinality value inspection.
- Pairwise covariance and correlation information.

The first release deliberately prioritizes **working end-to-end functionality, transparent implementation, and empirical testing** over building a highly specialized analytical engine.

---

## 2\. Guiding Philosophy: Build, Measure, Then Improve

The initial architecture follows a simple principle:

> **Make it work → verify correctness → measure behavior → identify bottlenecks → improve deliberately.**

Rather than immediately introducing a specialized analytical engine or a complicated out-of-core architecture, the quality checker was first implemented using standard Python and Pandas functionality.

This approach provides several advantages for a personal student project:

- The implementation remains understandable.
- Pandas provides familiar and well-tested dataframe operations.
- The statistical calculations can be independently tested with small deterministic fixtures.
- Performance can be measured against realistic datasets.
- Architectural weaknesses can be identified from actual behavior rather than assumptions.

This also means that some limitations discovered during development are intentionally retained in v1 rather than being hidden or prematurely redesigned.

---

# 3\. Core Architectural Decisions

## Decision 1: Pandas as the Primary Data-Processing Layer

### Choice

The quality checker is implemented primarily using **Pandas**, with CSV files processed through Pandas chunking.

### Rationale

Pandas provides the dataframe operations required by the quality checker without introducing additional analytical frameworks.

For the first release, the objective was not to build a replacement for Pandas or an industrial-scale data-processing engine. The objective was to determine how far a straightforward Pandas implementation could be pushed on a normal consumer machine.

Using Pandas also keeps the implementation compatible with the rest of the Python application and makes the resulting code easier to maintain.

### Trade-off

Pandas is not inherently an out-of-core analytical engine. Chunking therefore has to be designed explicitly, and any state retained between chunks can become a global memory consumer.

The quality checker consequently achieves bounded memory for many per-chunk calculations, but **the complete algorithm is not strictly constant-space**.

Several global structures intentionally grow with the dataset, most notably duplicate tracking.

---

## Decision 2: CSV Processing Uses Chunked Reading

### Choice

CSV files are processed incrementally using Pandas' `chunksize` functionality.

The production/default chunk size is **50,000 rows**.

A much smaller value of **5 rows** is used in the accuracy-test configuration because the dedicated test fixture contains only 10 rows and is specifically designed to force behavior across multiple chunks.

### Rationale

The 5-row test configuration is not a performance configuration. It exists to make chunk-dependent behavior deterministic and easy to exercise during automated testing.

The 50,000-row production value was selected separately as a practical starting point for performance testing on the project's target consumer hardware.

Benchmarking indicated that chunk size affects the balance between:

- Per-chunk processing overhead.
- Pandas allocation overhead.
- Temporary dataframe memory.
- Overall throughput.

Larger chunks can improve throughput but increase transient memory usage, particularly for text-heavy datasets.

### Trade-off

Chunking reduces the amount of input data that must be held simultaneously, but it does not automatically make every part of the algorithm memory-bounded.

For example:

```
Input file
↓
Chunk 1 → analyze → discard
Chunk 2 → analyze → discard
Chunk 3 → analyze → discard
...
```

works well for streaming statistics, but global structures such as duplicate hashes and unique-value sets survive across every chunk.

Therefore, the architecture should be described as **chunked processing with selected global state**, rather than as a completely constant-memory streaming engine.

---

## Decision 3: Excel Uses Whole-File Loading in v1

### Choice

`.xls` and `.xlsx` files are currently loaded using Pandas with the **Calamine engine**, after which the resulting dataframe is sliced into smaller chunks for compatibility with the same processing loop used by CSV input.

Conceptually:

```
Excel file
↓
Read complete workbook
↓
DataFrame in memory
↓
Artificial chunk slicing
↓
Shared analysis pipeline
```

### Why This Was Chosen

The original goal was to provide streaming behavior for both CSV and Excel.

During development, however, it became apparent that the current Excel ingestion strategy did not provide the same straightforward row-streaming model available from `pd.read_csv(..., chunksize=...)`.

Rather than redesign the entire Excel ingestion layer for the first release, the implementation loads the workbook and then reuses the existing chunk-processing architecture on the resulting dataframe.

This was considered a reasonable v1 trade-off because CleanSheet is a personal student project and the primary objective was to deliver a functional quality-checking feature rather than solve general-purpose out-of-core Excel processing.

### Calamine Decision

The Calamine engine was selected based on research indicating that its Rust-based implementation can provide faster spreadsheet parsing than commonly used Python Excel engines in some workloads.

However, the project has **not yet performed a controlled benchmark proving this claim against the alternative engines used during development**.

Therefore, this should be treated as an implementation choice informed by research rather than an experimentally established performance conclusion.

Future benchmarking should compare at least:

- Default Pandas Excel engine behavior.
- `openpyxl`.
- `calamine`.

The comparison should measure both execution time and peak memory consumption using the same datasets and hardware.

### Trade-off

Excel currently has a fundamentally different memory profile from CSV.

CSV can stream input rows from disk, while the current Excel implementation first creates a complete dataframe.

Consequently, Excel processing can require memory proportional to the workbook/dataframe size before the quality-analysis loop begins.

This is one of the major architectural limitations targeted for future improvement.

---

# 4\. Single-Pass Statistical Accumulation

## Decision 4: Running Accumulators for Univariate Statistics

### Choice

The quality checker calculates global numeric statistics using running accumulators rather than retaining all numeric observations.

The primary accumulated quantities are:

- $\\sum x$
- $\\sum x^2$
- $n$

These are used to calculate:

- Mean.
- Population variance.
- Population standard deviation.
- Sample variance.
- Sample standard deviation.

### Rationale

The statistics can be calculated across independent chunks without retaining the complete numeric columns.

For example:

```
Chunk 1 → partial sum/count
Chunk 2 → partial sum/count
Chunk 3 → partial sum/count
            ↓
    global statistics
```

This allows the raw chunk to be discarded after processing.

The approach also avoids requiring a second pass through the source file.

### Trade-off

The implementation uses the computational shortcut:

$$
Var(X) = \frac{\sum x^2}{n} - \bar{x}^2
$$

and its corresponding sample-variance formulation.

This approach is simple and efficient, but it can suffer from **floating-point cancellation** when values are extremely large relative to their variance.

A numerically more stable online algorithm such as **Welford's algorithm** would be preferable for a future version.

This limitation was identified after the initial implementation had already been built and tested. Rather than redesigning the statistical engine during v1, the limitation was accepted and documented as future work.

### Future Improvement

Replace the current variance accumulation with a numerically stable online algorithm while preserving chunk-wise processing.

---

# 5\. Pairwise Covariance Architecture

## Decision 5: Eager Pairwise Numeric Analysis

### Choice

The engine evaluates every combination of numeric columns:

$$
\binom{K}{2} = \frac{K(K-1)}{2}
$$

where $K$ is the number of numeric columns.

For every pair, the engine maintains joint accumulators for:

- Number of overlapping observations.
- $\\sum x$.
- $\\sum y$.
- $\\sum xy$.

These values are later used to calculate sample covariance and population covariance.

Pearson correlation is then derived from sample covariance and the corresponding sample standard deviations.

### Rationale

The quality checker was designed to return a complete report after a single audit operation.

Automatically calculating all numeric relationships means the GUI can display the available relationship information without requiring a second analytical pass.

### Trade-off

The number of pairs grows quadratically with the number of numeric columns.

For example:

```
10 numeric columns  → 45 pairs
20 numeric columns  → 190 pairs
50 numeric columns  → 1,225 pairs
100 numeric columns → 4,950 pairs
```

The pairwise calculation also creates temporary masks and Series during chunk processing.

This makes covariance analysis a potential CPU and allocation bottleneck on wide datasets.

### Architectural Limitation

The current design intentionally favors **complete eager analysis** over selective analysis.

A future version could calculate covariance and correlation lazily, for example only when the user opens a statistical relationship view in the GUI.

---

# 6\. Cross-Chunk Duplicate Detection

## Decision 6: Store Row Hashes Rather Than Complete Rows

### Choice

Each processed row is converted into a Pandas-generated hash using:

```
pd.util.hash_pandas_object(chunk, index=False)
```

The resulting hashes are stored in a global Python `set`.

The duplicate count is then derived from:

```
duplicate_counts = total_rows - len(is_seen)
```

### Rationale

The engine only needs to determine **how many duplicate rows exist**.

It does not currently need to preserve the original duplicate rows, their locations, or the complete row contents.

Storing complete rows would therefore retain substantially more information than the current feature requires.

Using a compact hash representation provides a much smaller logical representation of each row and allows average constant-time membership checks through the Python set.

Conceptually:

```
Complete row
    ↓
64-bit hash
    ↓
Python set
    ↓
seen / duplicate
```

### Important Limitation

The assumption that hashing produces a sufficiently large memory reduction has not yet been independently benchmarked against alternative duplicate-tracking representations.

The design was chosen based on the expectation that storing one 64-bit value per row would be more memory-efficient than retaining complete row data.

However, the Python `set` itself has substantial CPython memory overhead due to hash-table storage, allocation strategy, and object representation.

Therefore, the effective memory cost is **much larger than 8 bytes per unique row**.

The architecture should not claim that the duplicate tracker has a simple 8-byte-per-row memory footprint.

### Complexity

If $U$ is the number of unique rows:

- Average lookup: $O(1)$.
- Space: $O(U)$.

This global set is currently the most important unbounded memory structure in the CSV processing path.

### Empirical Boundary

This limitation has been observed experimentally.

The benchmark containing approximately 100 million rows eventually exhausted the available system memory and was terminated by the Linux OOM killer.

This behavior is consistent with the linear growth of the global hash set.

### Future Improvement

Potential alternatives include:

- Disk-backed duplicate tracking.
- Database-backed uniqueness tracking.
- External sorting.
- Probabilistic duplicate detection where exact counts are not required.
- More memory-efficient native hash structures.

The appropriate solution depends on whether CleanSheet must preserve exact duplicate counts.

---

# 7\. Cardinality Tracking

## Decision 7: Cap Stored Unique Values

### Choice

The engine tracks distinct non-null values for columns until the number of stored values exceeds:

```
MAX_UNIQUE_VALUE = 1_000
```

Once the threshold is exceeded, the column is classified as:

```
High Cardinality
```

and the previously accumulated set is discarded.

### Rationale

The GUI does not need millions of distinct values to determine whether a column is low-cardinality.

A bounded threshold allows the quality report to provide useful categorical information without intentionally retaining an unlimited number of strings.

The threshold of 1,000 is a **design choice**, not a scientifically derived or experimentally optimized value.

### Trade-off

Before the threshold is reached, the unique-value set grows with the number of distinct values.

Therefore, without the threshold, cardinality tracking would have:

$$
O(U)
$$

space complexity, where $U$ is the number of distinct values stored for a column.

With the current threshold, the tracker is bounded per column at approximately the chosen cardinality limit, subject to Python object and set overhead.

### Important Limitation

The project has not yet performed a dedicated benchmark determining whether 1,000 is the best threshold for:

- Memory consumption.
- GUI responsiveness.
- Typical spreadsheet workloads.
- Accuracy/usability of categorical inspection.

The value is currently a pragmatic product decision.

Future versions may expose this as configuration or determine a more appropriate threshold from actual usage.

---

# 8\. Sentinel-Value Detection

## Decision 8: Explicit Sentinel Token Matching

### Choice

The engine maintains a predefined collection of strings representing common missing-data and placeholder conventions.

Examples include:

- `?`
- `N/A`
- `missing`
- `unknown`
- `DK`
- `REF`
- `PNA`
- `#DIV/0!`
- `1970-01-01`
- `9999-12-31`

These values are counted separately from standard Pandas null values.

### Rationale

Real-world spreadsheet data frequently contains values that are semantically missing but technically valid strings.

For example:

```
NaN
?
N/A
unknown
REF
9999-12-31
```

A standard `isna()` check cannot identify every such convention.

Explicit sentinel detection therefore provides a practical additional layer of data-quality inspection.

### Trade-off

There is no universal sentinel vocabulary.

A token that represents missing data in one dataset may be a legitimate value in another.

For example:

```
"unknown"
```

could represent a missing value, but it could also legitimately occur as a person's surname, product description, or categorical value.

Likewise, dates such as `1970-01-01` may be legitimate dates in some datasets.

Therefore, sentinel matching is intentionally **heuristic rather than authoritative**.

### Future Improvement

Possible improvements include:

- Configurable sentinel lists.
- Column-specific sentinel rules.
- Case-insensitive normalization.
- Whitespace normalization.
- User-defined domain rules.
- Separate classifications for "missing", "placeholder", "error token", and "possible default".

The current list is a practical v1 collection rather than a claim of exhaustive coverage.

---

# 9\. Type-Drift Detection

## Decision 9: Use the First CSV Chunk as the Baseline Schema

### Choice

The first processed chunk establishes the baseline Pandas dtype for each column.

Subsequent chunks are compared against that baseline.

If a column's inferred dtype differs from the baseline, the corresponding column is flagged as having type drift.

Conceptually:

```
Chunk 1:
age → int64
    ↓
    baseline

Chunk 2:
age → int64
    ↓
    match

Chunk 3:
age → object
    ↓
    drift
```

### Rationale

Chunk-level inference can expose inconsistencies that would otherwise be hidden by whole-file dtype inference.

This is particularly useful for detecting columns that begin as numeric values and later contain strings or other incompatible representations.

### Trade-off

The baseline represents the **first chunk's inferred schema**, not necessarily the mathematically or semantically correct schema for the entire dataset.

This behavior is intentional in v1 because the goal is to detect changes in how the input is interpreted between chunks.

Excel currently behaves differently because the workbook is loaded as a whole before the artificial chunk loop begins.

The resulting format-dependent behavior is documented separately in `TEST_RESULT.md`.

---

# 10\. Overall Space Complexity

The quality checker should not be described as having universally constant memory usage.

Instead, its architecture can be summarized as:

```
Per-chunk dataframe state
    ↓
    bounded
    +
Global analysis state
    ↓
┌───────────────────────────┐
│ Running statistics        │ → O(K)
│ Pairwise statistics       │ → O(K²)
│ Cardinality sets          │ → bounded by threshold
│ Duplicate hash set        │ → O(U)
└───────────────────────────┘
```

Where:

- $K$ = number of columns/numeric columns, depending on the structure.
- $U$ = number of unique rows retained by duplicate tracking.

The dominant unbounded component for large CSV datasets is the global duplicate hash set.

This explains why increasing the input chunk size is not sufficient to solve the 100-million-row memory problem: the chunk itself is temporary, while the duplicate set continues accumulating for the lifetime of the audit.

---

# 11\. Why the v1 Architecture Is Still Valuable

The current implementation deliberately does not attempt to solve every scalability problem.

For a first-release personal project, the architecture successfully demonstrates several useful engineering concepts:

- Chunk-based data processing.
- Incremental statistical aggregation.
- Cross-chunk state management.
- Schema monitoring.
- Duplicate detection.
- Cardinality guardrails.
- Spreadsheet-format handling.
- Resource instrumentation.
- Automated correctness testing.
- Empirical performance testing.

More importantly, the limitations were not simply theoretical.

The project uses dedicated tests for correctness and a separate benchmark harness for resource behavior. These provide evidence for which parts of the architecture currently work and where the boundaries begin to appear.

The approximately 100-million-row benchmark, for example, demonstrated a real scalability boundary caused by global duplicate tracking rather than by the temporary processing chunk itself.

---

# 12\. Known Limitations and Future Improvements

The following limitations are intentionally accepted in v1.

| Area | Current Design | Limitation | Future Direction |
| --- | --- | --- | --- |
| CSV ingestion | Pandas chunking | Some global state remains unbounded | External/disk-backed state where required |
| Excel ingestion | Whole-file load + artificial chunks | Memory scales with loaded workbook | Investigate true streaming/read-only approaches |
| Excel engine | Calamine | Performance advantage has not been independently benchmarked | Controlled engine comparison |
| Variance | $\\sum x$, $\\sum x^2$ shortcut | Floating-point cancellation | Welford-style online algorithm |
| Duplicate detection | 64-bit hashes in Python set | $O(U)$ memory and significant CPython overhead | Disk-backed or native memory-efficient structures |
| Pairwise covariance | Eager $\\binom{K}{2}$ calculation | Quadratic growth with numeric width | Lazy/on-demand analysis |
| Cardinality | 1,000-value threshold | Threshold chosen pragmatically | Benchmark or configure threshold |
| Sentinels | Static token list | Domain-specific values may be missed or falsely flagged | Configurable/domain-aware rules |
| Type inference | First-chunk baseline | Depends on Pandas inference behavior | More explicit schema normalization |
| Statistics | Complete eager report | Some expensive metrics may not be needed by every user | Lazy analysis in future versions |

These limitations are part of the current engineering state rather than evidence that the project is unfinished or unusable.

They provide concrete directions for future iterations.

---

# 13\. Relationship to the Other Documentation

The quality-checker documentation is intentionally divided by purpose.

### `README.md`

Provides the high-level overview of the engine, benchmark methodology, hardware environment, and observed performance results.

### `TEST_RESULT.md`

Documents correctness testing, test fixtures, expected behavior, and accepted CSV/XLS/XLSX differences.

### `TROUBLESHOOTING.md`

Documents implementation problems encountered during development and the fixes applied to resolve them.

### `ARCHITECTURE_NOTES.md`

Documents **why the engine was designed this way**, what trade-offs were made, what assumptions remain unverified, and what architectural improvements are planned.

This separation prevents the same information from being repeated across multiple documents.

---

# 14\. Future Architectural Direction

The long-term direction is to preserve the simplicity of the current analysis pipeline while removing its most significant scalability boundaries.

Potential future improvements include:

1. **True streaming Excel ingestion** where practical.
2. **Numerically stable online statistics** such as Welford's algorithm.
3. **Memory-efficient or disk-backed duplicate detection.**
4. **Lazy covariance/correlation calculation.**
5. **Configurable or adaptive cardinality tracking.**
6. **Configurable and column-aware sentinel detection.**
7. **More explicit schema normalization across CSV and Excel formats.**
8. **Additional benchmarking of Excel parsing engines.**
9. **More comprehensive statistical validation against reference implementations.**

The goal is not to eliminate every limitation immediately.

The goal is to use testing and profiling to identify which limitations actually matter to CleanSheet users and then improve those areas deliberately.

---

## 15\. Final Design Position

CleanSheet's v1 quality checker is best understood as a **chunk-oriented Pandas profiling engine with selected global state**, rather than a fully out-of-core analytical system.

Its architecture intentionally favors:

- Simplicity over premature complexity.
- Practical desktop usability over extreme-scale processing.
- Explicit testing over assumptions.
- Measured limitations over undocumented behavior.
- Incremental improvement over premature optimization.

The current implementation is therefore not presented as the final architecture.

It is the first measured architecture: simple enough to understand, functional enough to use, and instrumented enough to reveal where the next engineering problems are.