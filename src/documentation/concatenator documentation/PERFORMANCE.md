## ⚡ Performance & Memory Optimization: Spreadsheet Concatenator

> **Note:** The benchmarks and architectural optimizations detailed below apply specifically to the **Spreadsheet Concatenator** feature (`tab_concat.py`). The Data Quality and Cleaner modules are currently designed for standard in-memory operations and will undergo separate optimization passes in the future.

To ensure the concatenation engine can merge massive, multi-gigabyte exports on standard office laptops without triggering Out-Of-Memory (OOM) crashes, `tab_concat.py` was engineered with out-of-core processing (chunking) and low-level memory management.

### 🖥️ Benchmarking Environment

* **Platform:** Linux (Google Colab standard CPU instance — 2 vCPUs, 12 GB RAM)
* **Profiling Tools:** Python standard library `tracemalloc` (peak Python-tracked memory allocation) and `time.perf_counter()` (execution time)
* **Methodology:** Isolated environment to minimize local OS background noise and measure Python-level memory allocation and execution time.

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
CSV files are processed using parameterized Pandas chunks and written directly to disk, keeping peak largely independent of total CSV file size. Excel files are currently loaded into memory with the Calamine engine before being written to CSV.

**2. Rust-Based Excel Parsing (XLSX)**
XLSX/XLS files are currently parsed using Pandas with the Calamine engine. Calamine provides a fast Rust-based parser and reduces parsing overhead compared with the previous approach. Excel files are still loaded into an in-memory DataFrame during ingestion; chunked Excel ingestion is outside the scope of V1.0.0.

**3. Constant-Memory Excel Exporting**
Writing large merged datasets back into .xlsx format is traditionally memory-intensive. The engine writes to a temporary CSV first, then streams chunks into XlsxWriter using constant_memory=True. This substantially reduces the memory required during XLSX generation by avoiding construction of the entire output workbook in memory.

**4. Native Memory Management**
Profiling revealed that forcing garbage collection (`gc.collect()`) after file processing introduced massive CPU overhead. Relying strictly on Python's native reference counting proved to be the most performant architecture, keeping RAM low without the CPU penalty.

### ⏱️ Benchmark Results

Testing was conducted using Python's built-in `tracemalloc` and `time.perf_counter()`.

**Ingestion & Parsing Trade-offs (Scenario A)**
| Engine | Chunk Size | Execution Time | Peak Python-Tracked Memory (RAM) |
| :--- | :--- | :--- | :--- |
| **Calamine** | 100,000 rows | 83.53 sec | 1,765.73 MB |
| **Calamine** | 20,000 rows | 80.79 - 92.75 sec | 448.80 MB |
| **Calamine** | 10,000 rows | 160.81 sec | **264.78 MB** |

**Excel Merging & Export (Scenario B)**
Merging four `.xlsx` files (~141,000 combined rows) and exporting them natively back to `.xlsx`. By parameterizing the chunk size across both the read and write phases, the Space-Time trade-off is clearly visible:
| Export Engine | Chunk Size | Execution Time (Avg) | Peak Python-Tracked Memory (Stable) |
| :--- | :--- | :--- | :--- |
| **`xlsxwriter` (constant memory)** | 30,000 rows | ~66.88 sec | **104.47 MB** |
| **`xlsxwriter` (constant memory)** | 50,000 rows | ~63.82 sec | 113.36 MB |
| **`xlsxwriter` (constant memory)** | 80,000 rows | **~61.64 sec** | 135.45 MB |

### 🧠 Engineering Takeaways

1. **The Write Bottleneck Solved:** By utilizing `xlsxwriter`'s constant memory streaming, the engine merged over 140,000 rows of Excel data while maintaining a microscopic memory footprint as low as ~104 MB.
2. **The Sweet Spot:** A chunk size of 50,000 provided the best balance in the tested workloads, offering good processing speed while keeping Python-tracked memory usage relatively low for consumer hardware.

**Conclusion:** The V1.0.0 concatenation pipeline demonstrates low-memory, chunked processing for large CSV datasets and memory-efficient XLSX export. Excel ingestion currently uses an in-memory DataFrame and therefore remains dependent on available system memory. Further out-of-core Excel processing is planned for a future optimization pass.