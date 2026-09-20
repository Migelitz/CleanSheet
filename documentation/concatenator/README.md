# 📊 Spreadsheet Concatenator

The **Spreadsheet Concatenator** is a desktop tool for combining multiple spreadsheet files into a single output file.

It is one of the components of the broader **CleanSheet** project, which is designed around spreadsheet-related workflows such as data quality checking, concatenation, and cleaning.

The Concatenator was originally created for personal use, with the goal of making it easier to combine large spreadsheet exports without repeatedly running into memory limitations.

The current V1 implementation supports:

* `.csv` input
* `.xlsx` input
* `.csv` output
* `.xlsx` output

It intentionally focuses on **vertical concatenation**: rows from one file are appended below the rows from another file.

> **Current V1 limitation:** `.xls` input/output is not supported. The original design intended to support `.xls`, `.xlsx`, and `.csv`, but `.xls` support was removed from V1 because the selected XLSX output library, XlsxWriter, does not support writing legacy `.xls` files. Supporting it properly would require a different architecture and additional implementation work.

---

## 🎯 Purpose

The original goal was simple:

> **Take multiple spreadsheet files and produce one merged spreadsheet.**

The project was not intended to become a full spreadsheet transformation or schema-management system.

The Concatenator therefore tries to preserve the input data as closely as possible rather than automatically modifying it.

Its primary responsibility is:

1. Read supported spreadsheet files.
2. Verify that their columns are compatible.
3. Append their rows.
4. Write the combined dataset to the requested output format.

It does **not** currently attempt to automatically repair, normalize, or transform the underlying dataset.

---

# 📥 Supported Input Formats

| Format  | Supported | Processing                                   |
| ------- | --------: | -------------------------------------------- |
| `.csv`  |         ✅ | Chunked with `pandas.read_csv()`             |
| `.xlsx` |         ✅ | Loaded into a DataFrame with Pandas/Calamine |
| `.xls`  |         ❌ | Not supported in V1                          |

The GUI currently allows users to select only CSV and XLSX files.

---

# 📤 Supported Output Formats

| Format  | Supported | Processing                     |
| ------- | --------: | ------------------------------ |
| `.csv`  |         ✅ | Written incrementally to disk  |
| `.xlsx` |         ✅ | Built from an intermediate CSV |
| `.xls`  |         ❌ | Not supported                  |

CSV is the preferred output format when working with datasets that may exceed Excel's worksheet row limit.

---

# 🔗 What Does "Concatenate" Mean?

The Concatenator performs **vertical row appending**.

For example:

```text
File A

Name    Age
Alice   20
Bob     21
```

and:

```text
File B

Name    Age
Charlie 22
David   23
```

become:

```text
Name    Age
Alice   20
Bob     21
Charlie 22
David   23
```

The header is written once.

The Concatenator is **not** currently a database-style `JOIN`, relational merge, or automatic schema-alignment system.

---

# 🧱 Column Compatibility

Input files must contain the same columns in the same order.

For example:

```text
File A:
Name | Age | City

File B:
Name | Age | City
```

is accepted.

But:

```text
File A:
Name | Age | City

File B:
Name | City | Age
```

is rejected.

Likewise:

```text
File A:
Name | Age | City

File B:
Name | Age | Country
```

is rejected.

This restriction exists because automatically aligning different schemas can introduce ambiguous behavior and unexpected output.

The current implementation therefore prefers **explicit failure over silently producing a malformed dataset**.

### Current limitation

Column names are compared exactly.

Therefore, differences such as:

```text
Name
```

versus:

```text
name
```

are currently treated as different columns.

Automatic case normalization is not implemented.

---

# 🧠 Data Preservation Philosophy

The Concatenator's responsibility is to **concatenate**, not to reinterpret the user's data.

The intended behavior is:

> **Preserve the values supplied by Pandas and append rows without intentionally transforming the dataset.**

This is especially important for values such as identifiers:

```text
000123
```

Automatically converting every numeric-looking value into a number could turn this into:

```text
123
```

which would destroy meaningful information.

For this reason, the Concatenator does not attempt to automatically normalize every column into a common datatype.

### Known dtype behavior

CSV and XLSX files can sometimes produce different Python/Pandas representations for the same logical value because their input formats are interpreted differently.

For example, a value such as:

```text
29.85
```

may be represented as a string in one input path and a floating-point value in another.

This behavior is currently accepted because automatic datatype normalization would conflict with the project's goal of avoiding unintended data transformation.

More details are documented in `TEST_RESULT.md`.

---

# ⚙️ Processing Architecture

The Concatenator uses different processing strategies depending on the input and output format.

## CSV Input

CSV files are processed using Pandas chunking:

```python
pd.read_csv(filepath, chunksize=chunksize)
```

Each chunk is written directly to the destination or intermediate CSV.

Conceptually:

```text
Large CSV
   │
   ├── Chunk 1 ──┐
   ├── Chunk 2 ──┤
   ├── Chunk 3 ──┤──> Output CSV
   └── Chunk N ──┘
```

This prevents the entire CSV from having to exist inside one large DataFrame.

---

## XLSX Input

XLSX files currently cannot be processed with the same chunked input mechanism.

The current approach is:

```text
XLSX
 │
 ▼
Pandas / Calamine
 │
 ▼
Entire XLSX DataFrame
 │
 ▼
CSV
```

The XLSX DataFrame therefore still occupies memory during ingestion.

This is an acknowledged V1 limitation.

The architecture was chosen after testing showed that attempting to load and concatenate multiple DataFrames with `pd.concat()` could consume excessive memory and trigger Linux's OOM killer.

Instead of:

```text
XLSX A ──> DataFrame A ──┐
XLSX B ──> DataFrame B ──┼──> pd.concat()
XLSX C ──> DataFrame C ──┘
```

the current architecture converts the files into a disk-backed CSV representation and appends the data incrementally.

---

# 💾 Why Not Simply Use `pd.concat()`?

This is one of the most important architectural decisions in the project.

The initial approach considered loading the files and using:

```python
pd.concat(...)
```

However, testing showed that this could consume extremely large amounts of RAM.

Even relatively small combinations of CSV/XLSX files produced unexpectedly high memory usage, and larger Excel combinations could trigger the Linux OOM killer and freeze the system.

The project therefore moved toward:

```text
Read
  ↓
Append
  ↓
Write to disk
```

instead of:

```text
Read everything
  ↓
Store everything in memory
  ↓
pd.concat()
  ↓
Write
```

The goal is not to eliminate memory usage entirely.

The goal is to avoid making **the entire merged dataset** dependent on RAM.

---

# 🔄 XLSX Output Pipeline

When the requested output is `.csv`, data can be written directly.

When the requested output is `.xlsx`, the program first creates a temporary CSV:

```text
Input files
    │
    ▼
stream_to_csv()
    │
    ▼
Temporary CSV
    │
    ▼
Read temporary CSV in chunks
    │
    ▼
XlsxWriter
    │
    ▼
Final XLSX
```

This allows the same concatenation pipeline to be reused for both CSV and XLSX output.

The temporary CSV is deleted after successful XLSX generation.

### Current limitation

If XLSX processing fails or is interrupted before cleanup, the temporary CSV can remain on disk.

This is known and is planned for a future cleanup improvement.

---

# 📊 Excel Row Limit

Excel worksheets have a maximum of **1,048,576 rows**.

The XLSX output path therefore checks whether the merged dataset exceeds the supported worksheet size.

If it does, the application warns the user and limits the XLSX output accordingly.

For larger datasets, CSV is recommended.

This limitation is specific to the Excel output format; the underlying CSV representation can contain substantially more rows.

---

# 🧪 Chunk Size

The default chunk size is:

```text
50,000 rows
```

The value was originally chosen as a practical starting point based partly on the Quality Checker implementation and the expectation that it would provide a reasonable balance between memory usage and execution time.

It is **not a universal optimal value**.

Users can configure the chunk size.

General behavior:

```text
Smaller chunks
    ↓
Lower memory usage
    ↓
Potentially more processing overhead

Larger chunks
    ↓
Higher memory usage
    ↓
Potentially less overhead
```

However, benchmarks performed during development showed that increasing the chunk size did not consistently produce meaningful throughput improvements for the tested workloads.

This suggests that beyond a certain point, increasing chunk size can provide diminishing performance returns while continuing to increase memory consumption.

Detailed measurements are documented in `TEST_RESULT.md`.

---

# 🖥️ GUI Architecture

The GUI is built using Tkinter and `tkinterdnd2`.

The processing logic is separated from the GUI.

Conceptually:

```text
┌─────────────────────────────┐
│          Tkinter GUI        │
│                             │
│ File selection              │
│ Drag & drop                 │
│ Output configuration        │
│ Progress window             │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│       Concatenation Core    │
│                             │
│ concat_files()              │
│ stream_to_csv()             │
└─────────────────────────────┘
```

This separation allows the processing functions to operate independently from the presentation layer.

A future version may further reorganize the implementation using classes/OOP if that provides a meaningful architectural benefit.

---

# 🧵 Background Processing

Concatenation runs in a background thread.

Without this, long-running operations would block Tkinter's main event loop and cause the interface to become unresponsive.

The application therefore separates:

```text
GUI thread
    │
    └── remains responsive

Background thread
    │
    └── performs concatenation
```

The progress indicator is intentionally **indeterminate**.

The application does not currently know the exact number of processing operations required for every combination of input files, chunks, and output formats, so displaying an exact percentage would imply a level of progress estimation that the current implementation does not provide.

---

# 🛡️ Validation

The current implementation validates several conditions, including:

* Destination folder exists.
* Destination is actually a directory.
* Output filename is not blank.
* Output extension is supported.
* Input file extensions are supported.
* Input columns match exactly.
* Excel output respects the worksheet row limit.

The GUI also prevents the same resolved file path from being added multiple times.

This duplicate prevention is primarily a **user-interface convenience**:

> Accidentally adding the same file twice should not silently duplicate the dataset.

---

# 🧪 Testing

The current functional test suite verifies the six primary format combinations:

| Input       | Output | Status |
| ----------- | ------ | -----: |
| CSV + CSV   | CSV    |      ✅ |
| XLSX + XLSX | XLSX   |      ✅ |
| CSV + CSV   | XLSX   |      ✅ |
| XLSX + XLSX | CSV    |      ✅ |
| CSV + XLSX  | CSV    |      ✅ |
| CSV + XLSX  | XLSX   |      ✅ |

The tests use `pytest` and `tmp_path` for temporary output locations and Pandas dataframe comparisons.

A previous bug involving multi-chunk XLSX writing caused one row to be overwritten because of incorrect `startrow`/header offset handling. That issue was identified during testing and corrected.

More details and benchmark results are documented in:

* `ARCHITECTURE_NOTES.md`
* `TEST_RESULT.md`

---

# 🚧 V1 Scope & Known Limitations

The following are intentionally outside the current V1 scope:

* ❌ XLS support
* ❌ Multiple worksheet processing
* ❌ Automatic column schema normalization
* ❌ Automatic column reordering
* ❌ Automatic datatype conversion
* ❌ Automatic missing-value normalization
* ❌ Parallel processing
* ❌ True streaming XLSX input
* ❌ Percentage-based progress
* ❌ Resume after interrupted processing
* ❌ Compression
* ❌ Database-backed processing
* ❌ Cloud storage

These are not necessarily impossible features.

They are simply outside the current implementation scope.

---

# 🔮 Future Improvements

Possible future development includes:

* True streaming XLSX input
* XLS support
* Support for additional spreadsheet formats
* Better temporary-file cleanup after failure
* Progress percentage
* Better datatype handling
* Optional schema alignment
* Parallel processing
* More efficient CSV/XLSX writing
* Configurable chunking improvements
* More comprehensive validation
* Improved GUI design
* Additional quality-of-life features

---

# 🧭 Development Philosophy

The Concatenator follows a simple development philosophy:

> **Make it work first. Optimize later.**

The architecture evolved through actual failures and measurements.

The initial `pd.concat()` approach was replaced after memory problems and OOM events.

CSV chunking was introduced to reduce memory pressure.

XLSX files were routed through an intermediate CSV because direct chunked XLSX ingestion was not available in the chosen implementation.

Benchmarks were then used to determine whether larger chunk sizes actually provided meaningful performance benefits.

This means V1 is intentionally not presented as a perfect or universally optimal architecture.

It is a practical implementation that works within the tested environment while leaving room for future optimization.

---

# 📚 Documentation

| File                    | Purpose                                                                   |
| ----------------------- | ------------------------------------------------------------------------- |
| `README.md`             | Overview, features, architecture, limitations                             |
| `ARCHITECTURE_NOTES.md` | Design decisions, reasoning, trade-offs, and future direction             |
| `TEST_RESULT.md`        | Functional tests, benchmarks, observed behavior, and accepted limitations |

---

# ✅ Current Status

**V1 — Functional and tested**

The current implementation successfully handles the primary CSV/XLSX concatenation workflows tested during development.

Its main architectural strength is its ability to avoid the memory behavior encountered with full in-memory `pd.concat()` workflows.

Its main architectural limitation is that XLSX input is still loaded into memory before being converted into the disk-backed CSV pipeline.

The project therefore represents a practical V1 rather than a final high-performance spreadsheet processing engine.
