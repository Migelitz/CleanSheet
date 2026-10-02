# CleanSheet

### One Click, Data Clean!

CleanSheet is a Python desktop application for spreadsheet data processing and automation. It brings common spreadsheet workflows into a single graphical interface, allowing users to **combine, inspect, clean, and transform datasets** without having to write a new script for every file.

CleanSheet was originally built as a personal automation project and portfolio project, and has grown into a complete desktop application focused on practical spreadsheet workflows, resource-aware processing, testing, and maintainable software design.

<!-- SCREENSHOT PLACEHOLDER
Add a screenshot of the main CleanSheet interface here.

Recommended path:
assets/screenshots/main-interface.png

Example:
![CleanSheet Main Interface](assets/screenshots/main-interface.png)
-->

---

## Demo

<!-- VIDEO PLACEHOLDER
Add the CleanSheet demo video here.

On GitHub, you can replace this placeholder by dragging the demo video into the README editor.
-->

The demo showcases the main CleanSheet workflow, including spreadsheet concatenation, data quality checking, and spreadsheet cleaning.

---

## What Is CleanSheet?

CleanSheet is designed around a simple idea:

> **Common spreadsheet tasks should be reusable instead of requiring a new script every time.**

Instead of manually repeating the same data-processing steps or creating separate Pandas scripts for different datasets, CleanSheet provides configurable tools through a desktop GUI.

The application currently contains four main tabs:

* **Spreadsheet Concatenator** — combine compatible spreadsheet files into one dataset.
* **Data Quality Checker** — inspect a dataset for structural, missing-value, numerical, duplication, statistical, and cardinality-related issues.
* **Spreadsheet Cleaner** — configure cleaning and transformation operations before exporting the processed dataset.
* **About** — project information, links, and feedback options.

The three data-processing tools can be used independently depending on the task.

---

# Features

## Spreadsheet Concatenator

Combine multiple CSV or XLSX files into a single output file.

The Concatenator focuses on **combining data rather than modifying it**. It validates the input files and their schemas before appending their rows into the final dataset.

<!-- SCREENSHOT PLACEHOLDER
Recommended path:
assets/screenshots/concatenator.png

Example:
![Spreadsheet Concatenator](assets/screenshots/concatenator.png)
-->

### Highlights

* Combine multiple CSV or XLSX files.
* Export to CSV or XLSX.
* Validate compatible column names and order.
* Process large CSV inputs in chunks.
* Use a disk-backed workflow for XLSX output.
* Validate Excel worksheet row limits.
* Prevent duplicate file selections.
* Run processing outside the GUI thread to keep the interface responsive.

[Read the Spreadsheet Concatenator documentation →](documentation/concatenator/README.md)

---

## Data Quality Checker

Profile a spreadsheet and identify potential data-quality issues before cleaning or analysis.

The Quality Checker examines different aspects of a dataset, including structure, missing values, numerical statistics, duplicates, relationships between numerical columns, and categorical cardinality.

<!-- SCREENSHOT PLACEHOLDER
Recommended path:
assets/screenshots/quality-checker.png

Example:
![Data Quality Checker](assets/screenshots/quality-checker.png)
-->

### Highlights

* Inspect dataset dimensions and column names.
* Detect empty columns.
* Analyze missing values and percentages.
* Identify common sentinel values.
* Inspect numerical ranges and statistics.
* Detect duplicate rows.
* Calculate covariance and Pearson correlation for numerical columns.
* Inspect categorical values and cardinality.
* Process CSV files using chunks.
* Analyze Excel files through the same quality-checking pipeline.

[Read the Data Quality Checker documentation →](documentation/quality_checker/README.md)

---

## Spreadsheet Cleaner

Clean and transform spreadsheet data through a configurable graphical interface.

The Cleaner provides common operations such as whitespace cleanup, character removal, missing-value handling, duplicate removal, and column transformations.

<!-- SCREENSHOT PLACEHOLDER
Recommended path:
assets/screenshots/cleaner.png

Example:
![Spreadsheet Cleaner](assets/screenshots/cleaner.png)
-->

### Highlights

* Trim whitespace.
* Remove selected characters.
* Handle missing values.
* Remove duplicate rows.
* Apply column-specific transformations.
* Export cleaned data to CSV or XLSX.
* Support CSV, XLSX, and XLS files.
* Process large CSV files in chunks.
* Track duplicates across CSV chunks.
* Keep processing outside the GUI thread.

Available transformations include:

* Keep Original
* lowercase
* UPPERCASE
* Title Case
* Date `YYYY-MM-DD`
* Numbers Only
* Clean Currency
* Extract Email
* Extract URL
* Anonymize Email
* Anonymize Numbers
* Split Human Names

[Read the Spreadsheet Cleaner documentation →](documentation/cleaner/README.md)

---

# Supported Formats

| Component                | CSV | XLSX | XLS |
| ------------------------ | :-: | :--: | :-: |
| Spreadsheet Concatenator |  ✅  |   ✅  |  ❌  |
| Data Quality Checker     |  ✅  |   ✅  |  ✅  |
| Spreadsheet Cleaner      |  ✅  |   ✅  |  ✅  |

Processing behavior and limitations vary between formats and components. See the individual feature documentation for the details.

---

# Main Interface

CleanSheet keeps its major workflows in separate tabs so each task can be performed independently.

```text
                         CleanSheet
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
  Concatenator        Quality Checker          Cleaner
        │                    │                    │
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                             ▼
                      Prepared Dataset
```

### Spreadsheet Concatenator

Combine compatible spreadsheet files.

### Data Quality Checker

Inspect a dataset before making changes to it.

### Spreadsheet Cleaner

Apply configurable cleaning and transformation rules.

### About

View project information, repository links, GitHub profile information, and feedback options.

---

# Typical Workflow

CleanSheet does not force users into a single workflow. The tools can be used independently, but a common data-preparation process might look like this:

```text
                    CleanSheet
                        │
             ┌──────────┼──────────┐
             ▼          ▼          ▼
        Concatenate   Inspect     Clean
             │          │          │
             └──────────┼──────────┘
                        ▼
                 Prepared Dataset
```

For example:

1. **Concatenate** several compatible spreadsheet files.
2. **Inspect** the resulting dataset with the Quality Checker.
3. **Clean** or transform the data using the Spreadsheet Cleaner.
4. Export the resulting dataset for further use.

These steps are conceptual; CleanSheet does not automatically chain the three components together.

---

# Why I Built CleanSheet

CleanSheet started as a personal automation project to reduce repetitive spreadsheet-processing work.

Instead of creating a separate Pandas script for every dataset, I wanted a reusable desktop application where common operations could be configured through a graphical interface.

The project eventually became much larger than the original idea. Along the way, it became an opportunity to explore:

* Python desktop application development
* Pandas-based data processing
* Large-file processing strategies
* Memory-aware workflows
* Multithreaded GUI processing
* Spreadsheet format handling
* Automated testing
* Performance benchmarking
* Data-quality analysis
* Software architecture and separation of concerns

CleanSheet is both a practical tool and a portfolio project demonstrating how a Python application can grow from a simple automation idea into a more complete piece of software.

---

# Design Goals

CleanSheet was developed around several goals.

### Practical Automation

Reduce repetitive spreadsheet work through reusable tools.

### Accessible Data Processing

Expose common data-processing operations through a graphical interface rather than requiring users to write Pandas code.

### Resource Awareness

Consider memory usage and processing behavior when working with larger datasets.

### Explicit Behavior

Make cleaning and data-processing operations configurable and predictable rather than silently changing data.

### Maintainability

Keep GUI logic, processing logic, testing, and documentation organized so that individual components can be developed and evaluated independently.

---

# Technology

| Technology          | Purpose                                 |
| ------------------- | --------------------------------------- |
| **Python 3.12+**    | Application and processing logic        |
| **Pandas**          | Spreadsheet and tabular-data processing |
| **Tkinter**         | Desktop graphical interface             |
| **tkinterdnd2**     | Drag-and-drop file support              |
| **Python Calamine** | Excel workbook ingestion                |
| **OpenPyXL**        | XLSX processing                         |
| **XlsxWriter**      | XLSX generation                         |
| **xlrd**            | Legacy XLS support                      |
| **NumPy**           | Numerical processing                    |
| **Nuitka**          | Release compilation                     |

CleanSheet uses a Python-based desktop architecture with the GUI separated from the core data-processing responsibilities of each feature.

---

# Architecture at a Glance

```text
                         CleanSheet GUI
                              │
             ┌────────────────┼────────────────┐
             │                │                │
             ▼                ▼                ▼
       Concatenator     Quality Checker      Cleaner
             │                │                │
             └────────────────┼────────────────┘
                              │
                              ▼
                     Python / Pandas
                              │
                              ▼
                    Spreadsheet I/O
```

The root README intentionally keeps the architecture high-level.

Each feature has its own documentation containing deeper explanations of implementation decisions, processing strategies, testing, benchmarks, and limitations.

---

# Testing & Validation

CleanSheet has been evaluated using several types of testing:

* Automated functional tests
* Manual GUI testing
* File-format testing
* Large-workload benchmarks
* Memory and processing measurements
* Edge-case validation

The development process also included workload-specific benchmarking for larger spreadsheet datasets.

The benchmark results are intended to document observed behavior on the development machine rather than provide universal performance guarantees.

Detailed testing information is available in each component's documentation and test-result files.

---

# Download

CleanSheet releases are distributed as compiled applications for:

* **Linux**
* **Windows**

Release builds are compiled using **Nuitka**.

### Latest Release

[Download CleanSheet from GitHub Releases](https://github.com/Migelitz/CleanSheet/releases)

Release users should use the appropriate compiled build for their operating system.

---

# Development Setup

CleanSheet requires:

* Python 3.12+
* [uv](https://docs.astral.sh/uv/)
* Git

Clone the repository and install the project environment with:

```bash
uv sync
```

The application source code is located under:

```text
src/cleansheet/
```

The test suite is located under:

```text
tests/
```

Run the automated tests with:

```bash
uv run pytest
```

---

# Documentation

CleanSheet's detailed documentation is separated by feature.

### Spreadsheet Concatenator

[Feature README](documentation/concatenator/README.md)
[Architecture Notes](documentation/concatenator/ARCHITECTURE_NOTES.md)
[Test Results](documentation/concatenator/TEST_RESULT.md)

### Data Quality Checker

[Feature README](documentation/quality_checker/README.md)
[Architecture Notes](documentation/quality_checker/ARCHITECTURE_NOTES.md)
[Test Results](documentation/quality_checker/TEST_RESULT.md)
[Troubleshooting](documentation/quality_checker/TROUBLESHOOTING.md)

### Spreadsheet Cleaner

[Feature README](documentation/cleaner/README.md)
[Architecture Notes](documentation/cleaner/ARCHITECTURE_NOTES.md)
[Test Results](documentation/cleaner/TEST_RESULT.md)

---

# Current Status

**Version: 1.0.0**

CleanSheet 1.0.0 represents the first complete release of the application.

The three primary data-processing components have been implemented, tested, benchmarked, and documented:

* Spreadsheet Concatenator
* Data Quality Checker
* Spreadsheet Cleaner

The project is currently focused on being a practical desktop automation tool and a documented portfolio project.

---

# Known Limitations

CleanSheet 1.0.0 has limitations that vary by component and spreadsheet format.

Some examples include:

* Large Excel files can require substantially more memory than chunked CSV processing.
* The Concatenator does not currently support legacy XLS input.
* Spreadsheet schemas are expected to be compatible for concatenation.
* Duplicate detection is based on exact row equality.
* Some quality checks use heuristics and configurable thresholds.
* Certain statistical operations have computational or numerical limitations on very large datasets.
* The Cleaner does not automatically infer the correct cleaning rules for every dataset.

These limitations are documented in greater detail within the individual feature documentation.

---

# Future Direction

Potential future improvements include:

* More large-dataset processing improvements
* Expanded spreadsheet workflows
* Additional cleaning and transformation operations
* More validation capabilities
* Improved GUI/UX
* Additional performance testing
* Expanded spreadsheet-format support
* Further automation between data-processing workflows

These are possible directions rather than a fixed roadmap.

---

# Development Environment

The primary development and benchmarking environment used for CleanSheet is:

* **OS:** Linux Mint 22.3
* **Desktop Environment:** Xfce 4.18
* **CPU:** Intel Core i5-1035G1
* **RAM:** 8 GB
* **Architecture:** x86_64
* **Python:** 3.12+

Performance results should therefore be interpreted in the context of the hardware and workloads used during testing.

---

# License

CleanSheet is released under the **MIT License**.

See the full license in [LICENSE](LICENSE).