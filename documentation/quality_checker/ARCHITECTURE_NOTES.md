# Architecture Notes & Design Decisions

This document outlines the core architectural choices, empirical trade-offs, and design rationale behind the CleanSheet engine (`quality_checker.py`). Rather than prematurely optimizing with specialized frameworks, v1.0 was designed to test the limits of standard tools (Pandas) on consumer hardware, establish empirical baselines, and iterate based on benchmark data.

---

## 1. Guiding Philosophy: Make It Work, Measure, Then Optimize

The primary goal of the initial release was **end-to-end functionality under bounded memory**. Instead of adopting complex out-of-core query engines or native extensions immediately, the engine implements straightforward, native Python and Pandas pipelines to discover where performance bottlenecks actually occur. Incremental optimization guided by benchmarks was prioritized over adopting unfamiliar dependencies prematurely.

---

## 2. Core Decisions & Rationale

### Decision 1: Foundation on Pandas & Calamine Engine

* **Choice:** Build data pipelines around `pandas` chunking, paired with `python-calamine` for Excel parsing.


* **Rationale:** Pandas is the standard data manipulation library in Python, offering strong ecosystem familiarity and seamless integration with desktop GUI threads. Before introducing distributed or out-of-core libraries like Polars or DuckDB, the priority was determining whether a well-structured Pandas chunking pipeline could sufficiently handle real-world desktop workloads. Calamine was integrated because standard Excel engines (`openpyxl`, `xlrd`) are significantly slower when ingesting tabular data.


* **Trade-off:** Reading Excel files through `pd.read_excel(..., engine="calamine")` requires an in-memory load of the workbook before chunk slicing occurs. While CSVs achieve true stream-from-disk processing, Excel processing remains memory-bound by total file size.



### Decision 2: Chunk Sizing Heuristic (50,000 Rows Target)

* **Choice:** Standardize pipeline chunking at **50,000 rows** across modules (with 30,000 used during initial quality checker testing).


* **Rationale:** Chunk sizing was determined empirically on an 8 GB RAM target machine.


* **100,000+ rows:** While per-second throughput increases, memory spikes sharply on dense text datasets like `vehicles.csv`, threatening system memory limits.


* **30,000–40,000 rows:** Keeps resident memory low but increases Python iteration overhead and per-chunk function call cost, reducing overall processing speed.


* **50,000 rows:** Represents the empirical sweet spot, providing an optimal balance between execution throughput and manageable heap overhead on standard consumer hardware.





### Decision 3: Single-Pass Streaming Statistics

* **Choice:** Compute sample and population variance, standard deviation, and covariance in a **single pass** using running accumulators ($\sum x$, $\sum x^2$, $\sum xy$).


* **Rationale:** Two-pass algorithms (e.g., pass 1 calculating the global mean, pass 2 calculating squared differences) require either re-reading multi-gigabyte files from disk or holding intermediate state in memory. A single pass minimizes disk I/O and keeps execution moving forward continuously through the chunk generator.


* **Known Numerical Boundary:** Computational shortcut formulas are susceptible to floating-point catastrophic cancellation when calculating variance on datasets with very large values and very small variances ($\sum x^2 - \frac{(\sum x)^2}{n}$). While numerically stable online algorithms (such as Welford's algorithm) exist, the shortcut formula was chosen as a pragmatic baseline to achieve pure vectorized Pandas calculations across chunk series.



### Decision 4: Cross-Chunk Deduplication via 64-bit Hashes

* **Choice:** Hash each row into an unsigned 64-bit integer using `pd.util.hash_pandas_object()` and track uniqueness inside a global Python set (`is_seen = set()`).


* **Rationale:** In an out-of-core pipeline where rows arrive in independent chunks, identifying duplicates across chunks requires shared global state. Storing full row values in memory would defeat chunking and quickly exhaust system RAM. Compressing entire rows into 64-bit integers reduces the memory footprint while maintaining $O(1)$ duplicate lookups.


* **Identified Boundary:** While effective for small to medium datasets, native Python `set` structures introduce object boxing and hash table over-allocation (approximately 48–64 bytes per unique entry). When processing files with tens of millions of unique rows (such as the 100M-row `custom_1988_2020.csv`), this in-memory set exhausts physical RAM and triggers the OS Out-of-Memory (OOM) killer.



### Decision 5: Eager Calculation of Pairwise Covariance

* **Choice:** Automatically evaluate all combinations of numeric column pairs, $\binom{K}{2}$, across every chunk.


* **Rationale:** Designed to provide users with a complete, fully populated audit report immediately upon completion without requiring manual secondary triggers.


* **Identified Boundary:** On tables with many numeric columns ($K$), pairwise combinations grow quadratically. Slicing temporary boolean masks and Series within nested loops inside every chunk increases CPU utilization and memory churn, highlighting this as a prime candidate for lazy, on-demand calculation in future versions.



### Decision 6: Cardinality Guardrail (`MAX_UNIQUE_VALUE = 1_000`)

* **Choice:** Cap tracked distinct categorical values at 1,000 items per column. If a column exceeds this count, the tracker clears the set and labels the column `"High Cardinality"`.


* **Rationale:** A strict memory-capping safeguard. High-cardinality columns (e.g., UUIDs, transaction IDs, freeform text) would otherwise accumulate millions of string objects in memory, causing an uncontrolled heap leak. This threshold also keeps the UI master-detail viewer fast and responsive.



### Decision 7: Heuristic Domain Sentinel Token Matching

* **Choice:** Hardcode an exhaustive list of ~35 common sentinel markers (such as Excel errors like `#DIV/0!`, survey refusal codes like `REF` and `DK`, and epoch dates like `1970-01-01`).


* **Rationale:** Real-world spreadsheets rarely have clean missing data marked strictly as `NaN` or `None`. Data entry operators, legacy databases, and survey platforms frequently insert domain-specific strings to denote missingness. Explicitly scanning for these values flags hidden dirty data that standard parsers miss.



---

## 3. Retrospective & Future Optimization Roadmap

Testing and benchmarking established clear empirical baselines, confirming that the v1.0 design achieved its core goal: successfully streaming and auditing datasets on consumer hardware while isolating the exact structural limits of the engine.

| Architectural Component | Current v1.0 Baseline | Discovered Limitation | Next Iteration Strategy |
| --- | --- | --- | --- |
| **Duplicate Tracking** | In-memory Python `set` of 64-bit row hashes. | Scales as $O(U)$ RAM; causes OOM on 100M unique rows. | Transition to a space-bounded Bloom filter or disk-backed SQLite hash store. |
| **Pairwise Covariance** | Eager iteration over all column pairs via `itertools.combinations`. | $O(K^2)$ loop overhead and slice churn on wide numeric tables. | Make covariance on-demand, or vectorize via matrix multiplication ($X^T X$). |
| **Excel Ingestion** | Full workbook loaded via Calamine into DataFrame chunks. | Memory expands 5x–8x over disk size; not true streaming. | Explore event-driven SAX streaming (`openpyxl` read-only) for large spreadsheets. |
| **Variance Calculation** | Single-pass algebraic shortcut formulas ($\sum x^2 - \frac{(\sum x)^2}{n}$). | Susceptible to precision loss on ill-conditioned data. | Evaluate Welford’s or Chan's parallel/online variance algorithms across chunks. |
| **Sentinel Auditing** | `isin(sentinel_values)` executed on every column. | Redundant string token checking on clean numeric columns. | Restrict sentinel audits strictly to `object`, `string`, and `category` dtypes. |