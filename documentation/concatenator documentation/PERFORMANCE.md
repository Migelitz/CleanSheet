## ⚡ Performance & Memory Optimization: Spreadsheet Concatenator

> **Note:** The benchmarks and architectural optimizations detailed below apply specifically to the **Spreadsheet Concatenator** feature (`tab_concat.py`). The Data Quality and Cleaner modules are currently designed for standard in-memory operations and will undergo separate optimization passes in the future.

To ensure the concatenation engine can merge massive, multi-gigabyte exports on standard office laptops without triggering Out-Of-Memory (OOM) crashes, `tab_concat.py` was engineered with out-of-core processing (chunking) and low-level memory management.

### 🖥️ Benchmarking Environment

* **Platform:** Linux (Google Colab standard CPU instance — 2 vCPUs, 12 GB RAM)
* **Profiling Tools:** Python standard library `tracemalloc` (peak process memory) and `time.perf_counter()` (execution time)
* **Methodology:** Isolated environment to eliminate local OS background noise and measure purely deterministic process allocation.

### 📊 The Stress Test Datasets

The concatenator was benchmarked against two distinct heavy-load scenarios to test both ingestion and export limits.

**Scenario A: Massive CSV Ingestion (1.4 GB)**
| File Name | Format | File Size | Rows | Columns |
| :--- | :--- | :--- | :--- | :--- |
| `vehicles.csv` | CSV | 1.3 GB | 447,106 | 26 |
| `customer_churn.csv` | CSV | 954 KB | 7,043 | 21 |

**Scenario B: Multi-File Excel Merging & Export**
| File Name | Format | File Size | Rows | Columns |
| :--- | :--- | :--- | :--- | :--- |
| `100mb.xlsx` | XLSX | 100.8 MB | 27,000 | 8 |
| `12mb.xlsx` | XLSX | 12.0 MB | 42,000 | 8 |
| `13mb.xlsx` | XLSX | 13.0 MB | 46,000 | 8 |
| `sample-1mb.xlsx` | XLSX | 1.0 MB | 26,312 | 4 |

### 🏗️ Architecture Decisions

**1. Stream-to-Disk Chunking**
Instead of loading massive files into RAM simultaneously ($O(N)$ space complexity), the concatenator streams datasets into Pandas via parameterized chunks. It appends data directly to the disk output, allowing multi-gigabyte files to be processed with a flat memory footprint.

**2. Rust-Based Excel Parsing (XLSX)**
Standard Excel parsing (`openpyxl`) must load entire XML trees into memory, creating severe memory and CPU bottlenecks. We integrated the **Calamine** engine (a Rust-based Excel reader) to drastically accelerate parsing while capping memory bloat.

**3. Constant-Memory Excel Exporting**
Writing large merged datasets back into `.xlsx` format is traditionally memory-intensive. The engine writes to a temporary CSV first, then streams chunks into `xlsxwriter` using the `constant_memory=True` flag. This writes row-by-row directly to the hard drive, bypassing RAM bottlenecks entirely and intercepting Excel's 1,048,576 row limit safely.

**4. Native Memory Management**
Profiling revealed that forcing garbage collection (`gc.collect()`) after file processing introduced massive CPU overhead. Relying strictly on Python's native reference counting proved to be the most performant architecture, keeping RAM low without the CPU penalty.

### ⏱️ Benchmark Results

Testing was conducted using Python's built-in `tracemalloc` and `time.perf_counter()`.

**Ingestion & Parsing Trade-offs (Scenario A)**
| Engine | Chunk Size | Execution Time | Peak Memory (RAM) |
| :--- | :--- | :--- | :--- |
| **Calamine** | 100,000 rows | 83.53 sec | 1,765.73 MB |
| **Calamine** | 20,000 rows | 80.79 - 92.75 sec | 448.80 MB |
| **Calamine** | 10,000 rows | 160.81 sec | **264.78 MB** |

**Excel Merging & Export (Scenario B)**
Merging four `.xlsx` files (~141,000 combined rows) and exporting them natively back to `.xlsx`. By parameterizing the chunk size across both the read and write phases, the Space-Time trade-off is clearly visible:
| Export Engine | Chunk Size | Execution Time (Avg) | Peak Memory (Stable) |
| :--- | :--- | :--- | :--- |
| **`xlsxwriter` (constant memory)** | 30,000 rows | ~66.88 sec | **104.47 MB** |
| **`xlsxwriter` (constant memory)** | 50,000 rows | ~63.82 sec | 113.36 MB |
| **`xlsxwriter` (constant memory)** | 80,000 rows | **~61.64 sec** | 135.45 MB |

### 🧠 Engineering Takeaways

1. **The Write Bottleneck Solved:** By utilizing `xlsxwriter`'s constant memory streaming, the engine merged over 140,000 rows of Excel data while maintaining a microscopic memory footprint as low as ~104 MB.
2. **The Sweet Spot:** A chunk size of 50,000 provides the optimal balance across both read and write operations—processing gigabytes of data rapidly while strictly capping memory usage under safe thresholds for consumer hardware. 

**Conclusion:** The CleanSheet Concatenator module safely scales to multi-gigabyte datasets and heavy Excel workflows on standard hardware without freezing the host machine's operating system.