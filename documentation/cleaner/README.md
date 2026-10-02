# CleanSheet

CleanSheet is a Python desktop application for cleaning and transforming spreadsheet data through a graphical interface.

The main goal is to make repetitive spreadsheet-cleaning tasks easier without requiring the user to repeatedly write Pandas/Python code. Instead of manually creating a new cleaning script for every dataset, users can select a file, configure cleaning operations through the GUI, and export the processed result.

CleanSheet is primarily a portfolio project and a personal automation tool that I am building to support my own spreadsheet/data-handling work and future machine-learning workflows.

## Features

### Spreadsheet Cleaning

CleanSheet provides configurable cleaning operations including:

* Trim leading and trailing whitespace
* Remove selected characters from text columns
* Handle missing values
* Remove duplicate rows
* Transform individual columns
* Export cleaned data to CSV or XLSX

### Column Transformations

Transformations can be selected individually for specific columns.

Supported transformations include:

| Transformation                  | Description                                                   |
| ------------------------------- | ------------------------------------------------------------- |
| Keep Original                   | Leave the selected column unchanged                           |
| lowercase                       | Convert text to lowercase                                     |
| UPPERCASE                       | Convert text to uppercase                                     |
| Title Case                      | Convert text to title case                                    |
| Date (YYYY-MM-DD)               | Normalize dates into `YYYY-MM-DD` format                      |
| Numbers Only                    | Remove non-numeric characters                                 |
| Clean Currency                  | Remove currency formatting and convert values to numeric data |
| Extract Email                   | Extract an email address from text                            |
| Extract URL                     | Extract a URL from text                                       |
| Anonymize Email                 | Mask part of an email address                                 |
| Anonymize Numbers (Keep Last 4) | Mask digits while preserving the final four digits            |
| Split Human Names               | Extract first and last names into additional columns          |

For example, a column containing:

```text
Contact: alice.smith@example.com
```

can be transformed into:

```text
alice.smith@example.com
```

while a name column can be split into additional first-name and last-name columns.

### Large CSV Processing

CSV files are processed in chunks rather than loading the entire dataset into memory at once.

The current implementation uses a chunk size of 50,000 rows.

This was designed primarily around memory usage and the limitations of the development machine. During earlier development, loading a large dataset of approximately 426,000 rows and 26 columns into the GUI caused the application to become unresponsive and eventually crash.

CleanSheet therefore avoids loading the complete dataset when a file is initially selected. It reads the file headers first so the GUI can populate its column selectors without immediately loading all rows into memory.

### Background Processing

Spreadsheet processing runs in a background worker thread so that lengthy cleaning operations do not block the Tkinter interface.

The GUI can therefore remain responsive while the dataset is being processed.

## Processing Workflow

The cleaning workflow is approximately:

```text
Select spreadsheet
       ↓
Read file headers
       ↓
Configure cleaning options
       ↓
Start processing
       ↓
Read data
       ↓
Clean / transform data
       ↓
Remove duplicates when enabled
       ↓
Export result
```

For CSV → CSV processing, the data path is chunk-based:

```text
CSV file
   ↓
50,000-row chunk
   ↓
Clean chunk
   ↓
Remove duplicates
   ↓
Track previously encountered rows
   ↓
Write chunk
   ↓
Next chunk
   ↓
...
```

## Supported File Formats

| Input | Output | Processing     |
| ----- | ------ | -------------- |
| CSV   | CSV    | Chunked        |
| CSV   | XLSX   | Full DataFrame |
| XLSX  | CSV    | Full DataFrame |
| XLSX  | XLSX   | Full DataFrame |
| XLS   | CSV    | Full DataFrame |
| XLS   | XLSX   | Full DataFrame |

CSV → CSV is currently the only path that uses chunked processing.

Excel files are currently loaded into a complete Pandas DataFrame because the current implementation does not provide equivalent chunked processing for XLS/XLSX files.

## Duplicate Handling

Duplicate removal is based on exact duplicate rows.

Within a chunk, Pandas `drop_duplicates()` removes repeated rows.

For CSV → CSV processing, CleanSheet also maintains a set of hashes representing rows encountered in previous chunks. This allows duplicates that occur in different chunks to be detected without retaining all previously processed rows as complete DataFrame objects.

For example:

```text
Chunk 1
    Row A
    Row B

Chunk 2
    Row C
    Row A  ← already encountered

Result
    Row A
    Row B
    Row C
```

The current implementation uses row hashing as a practical way to track previously encountered rows. Hashing is not mathematically collision-free, and the performance/memory characteristics of this approach have not yet been independently benchmarked for different duplicate rates.

## Performance and Memory Design

Memory usage was one of the primary design considerations for CleanSheet.

The application was developed and tested on an 8 GB RAM laptop, so avoiding unnecessary full-dataset loading was particularly important.

The main strategies are:

* Read only headers when selecting a file
* Process CSV → CSV data in chunks
* Avoid keeping the entire CSV dataset in memory during chunked processing
* Track cross-chunk duplicates using hashes rather than retaining previous DataFrames
* Run processing outside the Tkinter GUI thread

These choices prioritize the ability to process larger CSV datasets without unnecessarily increasing memory consumption.

## Testing

CleanSheet has been tested using both automated tests and manual GUI testing.

Automated tests cover:

* Text trimming
* Character stripping
* Column transformations
* Missing-value handling
* Human-name splitting
* CSV/XLSX/XLS fixture processing
* CSV → XLSX conversion
* XLSX → CSV conversion

Manual testing covered:

* File selection
* Drag-and-drop
* Column transformations
* Missing-value options
* Duplicate removal
* Export
* Invalid input handling

Performance/resource benchmarks were also performed using 60,000-row CSV and XLSX datasets.

See [`TEST_RESULT.md`](TEST_RESULT.md) for the detailed QA results and benchmark measurements.

## v1.0.0 Limitations

The current version intentionally has several limitations:

* XLS/XLSX processing is not chunked
* No batch cleaning of multiple files in the cleaner tab
* No fuzzy duplicate detection
* Duplicate detection is based on exact row equality
* No automatic column-type inference
* No undo/history system
* No cloud or spreadsheet-service integration
* Cleaning rules cannot guarantee correct results for every possible dataset
* Cross-chunk duplicate tracking has not yet been benchmarked across different duplicate rates and larger datasets
* GUI behavior is primarily validated through manual testing rather than automated GUI tests

These limitations define the current scope of v1.0.0 rather than being claims that the application supports every possible spreadsheet workflow.

## Project Direction

CleanSheet is being developed as part of a broader interest in Python automation, data processing, and machine-learning-related workflows.

The long-term goal is to reduce repetitive manual spreadsheet/data-handling work by turning commonly repeated operations into reusable tools instead of repeatedly writing custom Pandas scripts.

Future improvements may include more performance testing, better handling of large datasets, improved duplicate-processing strategies, and additional automation features.

## Development Environment

The main development and benchmark environment is:

* OS: Linux Mint 22.3
* Desktop: Xfce 4.18
* CPU: Intel Core i5-1035G1
* RAM: 8 GB
* Python: 3.12
* Architecture: x86_64

The application is designed around Python and Pandas, with Tkinter providing the desktop GUI.
