# Data Quality Checker Engine

The `quality_checker` module provides streaming data profiling and schema validation for spreadsheet datasets. It is built to audit CSV and Excel files on standard consumer machines by maintaining bounded memory consumption where possible.

---

## 🔬 Benchmarking Methodology

All performance benchmarks were captured using an isolated instrumentation harness (`quality_benchmark.py`) to record deterministic hardware metrics without GUI overhead.

### Instrumentation Stack
* **Execution Timing:** Measured wall-clock duration via high-resolution `time.perf_counter()`.
* **OS Resident Memory (RSS):** Monitored using a dedicated background daemon thread (`SystemResourceMonitor`) running `psutil.Process().memory_info().rss` sampled every **50 milliseconds** (`interval_sec=0.05`).
  * **Baseline RAM:** Process memory immediately prior to audit execution.
  * **Peak Process RAM:** Highest Resident Set Size recorded across all 50 ms polling ticks.
  * **Net OS RAM Used:** The true operating-system-level memory delta ($\Delta = \text{Peak RSS} - \text{Baseline RSS}$).
* **Python Object Heap:** Profiled using Python's native `tracemalloc` module to distinguish internal heap allocations from native C/Rust library allocations (Pandas/Calamine).
* **CPU Utilization:** Sampled continuously via non-blocking `psutil.cpu_percent(interval=None)` during execution, extracting both average and peak multi-core utilization.
* **Throughput:** Evaluated across both dimensions:
  $$\text{Throughput}_{\text{rows}} = \frac{\text{Processed Rows}}{\Delta t} \quad (\text{rows/sec})$$
  $$\text{Throughput}_{\text{MB}} = \frac{\text{File Size (MB)}}{\Delta t} \quad (\text{MB/sec})$$

---

## ⚡ Performance & Benchmark Results

### Hardware Profile
* **CPU:** Intel Core i5-1035G1 @ 1.00 GHz (4 Cores / 8 Threads, Ice Lake)
* **RAM:** 8.00 GiB total (~7.52 GiB available to user space, 2.00 GiB Swap)
* **Storage:** TeamGroup 512 GB SATA III SSD (6.0 Gb/s)
* **OS / Kernel:** Linux Mint 22.3 Zena (x86_64, Kernel 7.0.0-31-generic)
* **Environment:** Python 3.12, Pandas 2.x, Calamine engine

---

### CSV Streaming Audits
CSV processing streams row blocks via `pd.read_csv(filepath, chunksize=30000, low_memory=False)`.

| Dataset | Rows | Columns | File Size | Covariance Pairs | Avg Execution Time | Avg Throughput | Peak Net RAM Used | Peak Process RAM |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Telco Customer Churn** | 7,043 | 21 | 0.93 MB | 3 | 0.423 sec | ~18,366 rows/sec | 8.26 MB | 74.34 MB |
| **Customer Spending (1M)** | 1,000,000 | 11 | 88.71 MB | 6 | 38.125 sec | ~26,755 rows/sec | 205.29 MB | 271.63 MB |
| **5M Sales Records** | 5,000,000 | 14 | 595.09 MB | 21 | 237.245 sec | ~21,278 rows/sec | 411.99 MB | 478.16 MB |
| **Used Vehicles** | 426,880 | 26 | 1.38 GB | 21 | 82.480 sec | ~5,347 rows/sec | 1,075.93 MB* | 1,142.04 MB |
| **custom_1988_2020.csv** | ~100,000,000 | 8 | 4.60 GB | Aborted | **FAILED (OOM)** | 0 rows/sec | > 7.50 GB (Exhausted) | Kernel SIGKILL (137) |

*\* Note on String Density: `vehicles.csv` contains freeform descriptions, full URLs, and long VIN values across 26 columns. Python allocates distinct heap pointers for text objects inside every 30k chunk, resulting in higher resident memory usage than processing 5 million scalar numeric rows.*

*Note on 100M Row Dataset Failure: `custom_1988_2020.csv` contains roughly 100 million rows. Even with 30k chunk streaming, storing 64-bit integer hashes in `is_seen = set()` scales linearly with unique row counts, exceeding the available 7.52 GiB of RAM plus 2 GiB swap and triggering the Linux Out of Memory (OOM) killer.*

---

### Excel (`.xlsx` & `.xls`) Ingestion
Because standard libraries do not support true out-of-core row generators for zipped XML workbooks, Excel files are loaded into memory first via the `calamine` engine and sliced into chunks artificially.

| Dataset | Rows | Columns | File Size | Covariance Pairs | Avg Execution Time | Avg Throughput | Peak Net RAM Used | Peak Process RAM |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **file_example_5000.xls** | 5,000 | 8 | 0.64 MB | 3 | 0.507 sec | ~10,053 rows/sec | 15.58 MB | 81.61 MB |
| **sample-1mb.xlsx** | 26,312 | 4 | 1.05 MB | 1 | 2.286 sec | ~13,167 rows/sec | 48.29 MB | 114.38 MB |
| **sample_10240kb.xlsx** | 61,439 | 9 | 11.44 MB | 3 | 9.123 sec | ~7,557 rows/sec | 235.76 MB | 302.05 MB |
| **12mb.xlsx** | 42,000 | 8 | 11.85 MB | 0 | 6.372 sec | ~7,318 rows/sec | 215.91 MB | 281.99 MB |
| **100mb.xlsx** | 27,000 | 8 | 100.81 MB | 0 | 6.699 sec | ~4,173 rows/sec | 407.70 MB | 476.40 MB |
| **retail-sales-data.xlsx** | 500,000 | 12 | 230.76 MB | 6 | 61.392 sec | ~8,220 rows/sec | 1,827.78 MB** | 1,893.92 MB |

*\*\* Note on Memory Amplification: `.xlsx` files are compressed ZIP archives containing raw XML sheets. When parsed into memory, expanding cell trees creates a 5x–8x memory footprint expansion over the compressed file size on disk.*

---

## ⚙️ Core Architecture Trade-offs

1. **True Streaming (CSV) vs. In-Memory Load (Excel):** CSV files process in bounded $O(1)$ memory relative to row count. Excel files require $O(N)$ memory proportional to the total workbook size before chunk generation begins.
2. **Global Duplicate Tracking:** The deduplication logic utilizes 64-bit row hashes stored in an in-memory set (`is_seen = set()`). While lookups run in $O(1)$ time, set allocation scales with the count of distinct rows ($O(U)$), creating a known memory constraint on high-cardinality datasets containing tens of millions of rows.
3. **Combinatorial Covariance:** Pairwise tracking evaluates $\binom{K}{2}$ pairs for $K$ numeric columns. Wider numeric tables require more CPU cycles and slice copies during chunk iteration.