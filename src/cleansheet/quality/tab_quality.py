import csv
import logging
import os
import random
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import pandas as pd
import xlrd
from openpyxl import load_workbook
from PIL import Image, ImageTk
from tkinterdnd2 import DND_FILES

from cleansheet.quality.quality_checker import check_quality
from cleansheet.paths import ASSETS_DIR

logger = logging.getLogger(__name__)

# ==============================================================================
# BUG FIX: tkinterdnd2 Compatibility Patch for Python 3.12+
# ==============================================================================
# ISSUE: 
# tkinterdnd2 relies on an older Tcl/Tk extension that fails to provide an 
# event serial number for drag-and-drop events. Instead of a number, it passes 
# the literal string "%#". Python 3.12+ strictly attempts to cast this string 
# to an integer (in `tkinter.__init__.py`), resulting in a fatal TclError.
#
# SOLUTION:
# We apply a monkey patch to Tkinter's internal event argument substitution 
# method (`tk.Misc._substitute`). We intercept the raw arguments, and if we 
# detect the broken "%#" string, we replace it with a dummy integer (0) before 
# passing it up to Tkinter's strict type-checkers. This prevents the crash.
# ==============================================================================

_orig_substitute = tk.Misc._substitute

def _patched_substitute(self, *args):
    # args[0] is typically the event serial number. If it is the broken string,
    # we replace it with 0. Otherwise, we leave the arguments untouched.
    if args and len(args) > 0 and args[0] == "%#":
        args = (0,) + args[1:]
    return _orig_substitute(self, *args)

# Apply the patch globally to Tkinter
tk.Misc._substitute = _patched_substitute

# ==============================================================================

def show_data(df: pd.DataFrame, filepath: str) -> None:

    parent_frame = tk.Toplevel()
    parent_frame.title("Data Preview")
    parent_frame.geometry("1100x500")

    # ----- Top information -----

    info_frame = ttk.Frame(parent_frame)
    info_frame.pack(
        fill="x",
        padx=10,
        pady=10
    )

    filename = Path(filepath).name

    file_label = ttk.Label(
        info_frame,
        text=f"File: {filename}",
        font=("TkDefaultFont", 12, "bold")
    )
    file_label.pack(side="left")

    # ----- Table frame -----

    table_frame = ttk.Frame(parent_frame)
    table_frame.pack(
        fill="both",
        expand=True,
        padx=10,
        pady=(0, 10)
    )

    tree = ttk.Treeview(
        table_frame,
        columns=list(df.columns),
        show="headings"
    )

    vertical_scrollbar = ttk.Scrollbar(
        table_frame,
        orient="vertical",
        command=tree.yview
    )

    horizontal_scrollbar = ttk.Scrollbar(
        table_frame,
        orient="horizontal",
        command=tree.xview
    )

    tree.configure(
        yscrollcommand=vertical_scrollbar.set,
        xscrollcommand=horizontal_scrollbar.set
    )

    # ----- Columns -----

    for column in df.columns:
        tree.heading(
            column,
            text=column
        )

        tree.column(
            column,
            width=140,
            anchor="w"
        )

    # ----- Populate table -----

    for row in df.itertuples(index=False, name=None):
        tree.insert(
            "",
            "end",
            values=row
        )

    # ----- Layout -----

    tree.grid(
        row=0,
        column=0,
        sticky="nsew"
    )

    vertical_scrollbar.grid(
        row=0,
        column=1,
        sticky="ns"
    )

    horizontal_scrollbar.grid(
        row=1,
        column=0,
        sticky="ew"
    )

    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    # ----- Quality button -----

    def open_quality_report() -> None:

        logger.info("Opening quality report for %s", Path(filepath).name)
        quality_button.config(
            text="Processing... Please wait",
            state=tk.DISABLED
        )

        # Progress bar
        progress_win = tk.Toplevel(parent_frame)
        progress_win.title("Progress")

        # Center the progress window on the screen
        window_width, window_height = 300, 120
        screen_width = progress_win.winfo_screenwidth()
        screen_height = progress_win.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        progress_win.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Make the progress window modal (block interaction with the main window)
        progress_win.transient(parent_frame.winfo_toplevel())
        progress_win.grab_set()

        ttk.Label(
            progress_win, 
            text="Generating quality report...\nPlease wait.",
            justify="center"
        ).pack(pady=15)
        
        progress = ttk.Progressbar(progress_win, mode="indeterminate")
        progress.pack(fill="x", padx=20)
        progress.start()

        def run_background_task() -> None:
            started_at = time.perf_counter()
            try:
                logger.info("Quality report generation started for %s", Path(filepath).name)
                # Fetch the quality report
                report = check_quality(filepath=Path(filepath))

                # IMPORTANT: Tkinter is NOT thread-safe. You cannot update the UI 
                # from a background thread. We use .after(0, ...) to push the 
                # report back to the Main Thread so it can safely draw the new window.
                duration = time.perf_counter() - started_at
                logger.info(
                    "Quality report generation completed for %s in %.2fs",
                    Path(filepath).name,
                    duration,
                )
                parent_frame.after(0, lambda: on_success(report))
            except Exception as e:
                duration = time.perf_counter() - started_at
                logger.exception(
                    "Quality report generation failed after %.2fs for %s",
                    duration,
                    Path(filepath).name,
                )
                parent_frame.after(0, lambda error=str(e): on_error(error))

        def on_success(report: dict) -> None:
            progress.stop()  # Stop the progress bar
            progress_win.grab_release()  # Release the grab on the progress window
            progress_win.destroy()  # Close the progress window

            # Display the quality report in a new window
            show_quality_report(report)
            quality_button.config(
                text="Check Data Quality",
                state=tk.NORMAL
            )

        def on_error(error: str) -> None:
            progress.stop()  # Stop the progress bar
            progress_win.grab_release()  # Release the grab on the progress window
            progress_win.destroy()  # Close the progress window

            messagebox.showerror(
                "Processing Error", 
                f"An error occurred while generating the report:\n\n{error}"
            )
            quality_button.config(
                text="Check Data Quality", 
                state=tk.NORMAL
            )

        # Start the background thread
        # daemon=True ensures the thread dies if the user closes the app
        threading.Thread(target=run_background_task, daemon=True).start()

    quality_button = ttk.Button(
        parent_frame,
        text="Check Data Quality",
        command=open_quality_report
    )

    quality_button.pack(
        pady=(0, 10)
    )

def show_quality_report(report: dict) -> None:

    parent_frame = tk.Toplevel()
    parent_frame.title("Quality Report")
    parent_frame.geometry("1100x600")

    # ========================================================
    # OVERVIEW
    # ========================================================

    overview_frame = ttk.Frame(parent_frame)
    overview_frame.pack(
        fill="x",
        padx=10,
        pady=10
    )

    overview_label = ttk.Label(
        overview_frame,
        text="DATA QUALITY OVERVIEW",
        font=("TkDefaultFont", 14, "bold"),
        anchor="center"
    )
    overview_label.pack(
        fill="x",
        pady=(0, 10)
    )

    # ----- Metric cards container -----

    metric_cards_num = 2

    cards_frame = ttk.Frame(overview_frame)
    cards_frame.pack(fill="x")

    for column in range(metric_cards_num):
        cards_frame.columnconfigure(column, weight=1)

    # ----- Helper function for metric cards -----

    def create_card(parent, title, value, column):
        card = ttk.Frame(
            parent,
            relief="solid",
            borderwidth=1
        )

        card.grid(
            row=0,
            column=column,
            padx=5,
            sticky="nsew"
        )

        ttk.Label(
            card,
            text=title,
            font=("TkDefaultFont", 9, "bold")
        ).pack(pady=(10, 2))

        ttk.Label(
            card,
            text=value,
            font=("TkDefaultFont", 16, "bold")
        ).pack(pady=(2, 10))

    # ----- Values -----

    create_card(
        cards_frame,
        "ROWS",
        f"{report['rows']:,}",
        0
    )

    create_card(
        cards_frame,
        "COLUMNS",
        f"{report['columns']:,}",
        1
    )

    # ========================================================
    # NOTEBOOK
    # ========================================================

    notebook = ttk.Notebook(parent_frame)
    notebook.pack(
        fill="both",
        expand=True,
        padx=10,
        pady=(0, 10)
    )

    # ========================================================
    # COLUMNS TAB
    # ========================================================

    columns_tab = ttk.Frame(notebook)
    notebook.add(
        columns_tab,
        text="Columns"
    )

    columns_tree = ttk.Treeview(
        columns_tab,
        columns=(
            "column",
            "dtype",
            "type_drift",
            "non_null",
            "non_null_percentage",
            "missing",
            "missing_percentage",
            "sentinels",
        ),
        show="headings"
    )

    columns_tree.heading("column", text="Column")
    columns_tree.heading("dtype", text="Data Type")
    columns_tree.heading("type_drift", text="Type Drift")
    columns_tree.heading("non_null", text="Non-Null")
    columns_tree.heading("non_null_percentage", text="Non-Null %")
    columns_tree.heading("missing", text="Missing")
    columns_tree.heading("missing_percentage", text="Missing %")
    columns_tree.heading("sentinels", text="Sentinel Count")

    columns_tree.column("column", width=180)
    columns_tree.column("dtype", width=100)
    columns_tree.column("type_drift", width=100, anchor="center")
    columns_tree.column("non_null", width=100, anchor="center")
    columns_tree.column("non_null_percentage", width=110, anchor="center")
    columns_tree.column("missing", width=100, anchor="center")
    columns_tree.column("missing_percentage", width=110, anchor="center")
    columns_tree.column("sentinels", width=120, anchor="center")

    col_h_scroll = ttk.Scrollbar(
        columns_tab,
        orient="horizontal",
        command=columns_tree.xview
    )

    col_v_scroll = ttk.Scrollbar(
        columns_tab,
        orient="vertical",
        command=columns_tree.yview
    )

    columns_tree.configure(
        xscrollcommand=col_h_scroll.set,
        yscrollcommand=col_v_scroll.set
    )

    columns_tree.grid(
        row=0,
        column=0,
        sticky="nsew"
    )

    col_h_scroll.grid(
        row=1,
        column=0,
        sticky="ew"
    )

    col_v_scroll.grid(
        row=0,
        column=1,
        sticky="ns"
    )

    columns_tab.rowconfigure(0, weight=1)
    columns_tab.columnconfigure(0, weight=1)

    # ----- Populate columns table -----

    for column in report["column_names"]:

        # Get the type drift status for the column; default to "No" if not present.
        # If type_drift is empty, it means no drift was detected for that column. If it has a value, it indicates a drift was found.
        has_drift = "Yes" if report.get("type_drifts", {}).get(column) else "No"

        columns_tree.insert(
            "",
            "end",
            values=(
                column,
                report.get("baseline_dtypes", {}).get(column, "Unknown"),
                has_drift,
                f"{report['non_null_counts'].get(column, 0):,}",
                f"{report['non_null_percentage'].get(column, 0):.2f}%",
                f"{report['null_counts'].get(column, 0):,}",
                f"{report['null_percentage'].get(column, 0):.2f}%",
                f"{report['sentinel_counts'].get(column, 0):,}"
            )
        )

    # ========================================================
    # STATISTICS TAB
    # ========================================================

    statistics_tab = ttk.Frame(notebook)
    notebook.add(
        statistics_tab,
        text="Statistics"
    )

    # Only show columns that actually have calculated stats (Numeric columns only)
    numeric_columns = list(report["numeric_counts"].keys())

    if numeric_columns:

        statistic_columns = [
            "column",
            "count",
            "sum",
            "mean",
            "var (sample)",
            "std (sample)",
            "var (population)",
            "std (population)",
            "min",
            "max",
            "zeros",
            "negatives"
        ]

        statistics_tree = ttk.Treeview(
            statistics_tab,
            columns=statistic_columns,
            show="headings"
        )

        for col in statistic_columns:
            statistics_tree.heading(col, text=col.capitalize())
            statistics_tree.column(col, width=150, anchor="center")

        statistics_tree.column("column", width=180, anchor="w")

        stat_v_scroll = ttk.Scrollbar(
            statistics_tab,
            orient="vertical",
            command=statistics_tree.yview
        )

        stat_h_scroll = ttk.Scrollbar(
            statistics_tab,
            orient="horizontal",
            command=statistics_tree.xview
        )

        statistics_tree.configure(
            yscrollcommand=stat_v_scroll.set,
            xscrollcommand=stat_h_scroll.set
        )

        statistics_tree.grid(row=0, column=0, sticky="nsew")
        stat_v_scroll.grid(row=0, column=1, sticky="ns")
        stat_h_scroll.grid(row=1, column=0, sticky="ew")

        statistics_tab.rowconfigure(0, weight=1)
        statistics_tab.columnconfigure(0, weight=1)

        # ----- Populate statistics -----

        for col in numeric_columns:
            
            mean_val = report["global_mean"].get(col)
            sum_val = report["running_sum"].get(col)
            var_sample_val = report["sample_variance"].get(col)
            std_sample_val = report["sample_std"].get(col)
            var_population_val = report["population_variance"].get(col)
            std_population_val = report["population_std"].get(col)
            
            statistics_tree.insert(
                "",
                "end",
                values=(
                    col,
                    f"{report['numeric_counts'].get(col, 0):,}",
                    f"{mean_val:,.2f}" if mean_val is not None else "N/A",
                    f"{sum_val:,.2f}" if sum_val is not None else "N/A",
                    f"{var_sample_val:,.2f}" if var_sample_val is not None else "N/A",
                    f"{std_sample_val:,.2f}" if std_sample_val is not None else "N/A",
                    f"{var_population_val:,.2f}" if var_population_val is not None else "N/A",
                    f"{std_population_val:,.2f}" if std_population_val is not None else "N/A",
                    f"{report['global_min'].get(col, 'N/A')}",
                    f"{report['global_max'].get(col, 'N/A')}",
                    f"{report['zero_counts'].get(col, 0):,}",
                    f"{report['negative_counts'].get(col, 0):,}"
                )
            )

    else:

        ttk.Label(
            statistics_tab,
            text="No numerical columns available.",
            font=("TkDefaultFont", 11)
        ).pack(pady=30)

    # ========================================================
    # COVARIANCE TAB (New Pairwise Tab)
    # ========================================================

    cov_tab = ttk.Frame(notebook)
    notebook.add(cov_tab, text="Covariances")

    cov_data = report.get("sample_covariance", {})
    
    if cov_data:
        cov_tree = ttk.Treeview(
            cov_tab, 
            columns=(
                "col_x", 
                "col_y", 
                "sample_cov", 
                "pop_cov",
                "pearson"
            ), 
            show="headings"
        )

        cov_tree.heading("col_x", text="Column X")
        cov_tree.heading("col_y", text="Column Y")
        cov_tree.heading("sample_cov", text="Sample Covariance")
        cov_tree.heading("pop_cov", text="Population Covariance")
        cov_tree.heading("pearson", text="Pearson Correlation")

        for col in ("col_x", "col_y", "sample_cov", "pop_cov", "pearson"):
            cov_tree.column(col, width=150, anchor="center")

        cov_v_scroll = ttk.Scrollbar(
            cov_tab, 
            orient="vertical", 
            command=cov_tree.yview
            )
        cov_tree.configure(yscrollcommand=cov_v_scroll.set)

        cov_tree.pack(
            side="left", 
            fill="both", 
            expand=True
        )
        cov_v_scroll.pack(side="right", fill="y")

        for (col_x, col_y), s_cov in cov_data.items():
            p_cov = report.get("population_covariance", {}).get((col_x, col_y))
            pearson = report.get("pearson_correlation", {}).get((col_x, col_y))
            
            cov_tree.insert("", "end", values=(
                col_x,
                col_y,
                f"{s_cov:,.4f}" if s_cov is not None else "N/A",
                f"{p_cov:,.4f}" if p_cov is not None else "N/A",
                f"{pearson:,.4f}" if pearson is not None else "N/A"
            ))
    else:
        ttk.Label(
            cov_tab, 
            text="Not enough numeric columns to generate pairs.", 
            font=("TkDefaultFont", 11)
        ).pack(pady=30)

    # ========================================================
    # UNIQUE VALUES TAB (Master-Detail)
    # ========================================================

    unique_tab = ttk.Frame(notebook)
    notebook.add(
        unique_tab,
        text="Unique Values"
    )

    # The PanedWindow allows the user to drag the divider left or right
    paned_window = ttk.PanedWindow(unique_tab, orient="horizontal")
    paned_window.pack(fill="both", expand=True, padx=10, pady=10)

    # --- LEFT PANE (Master - Column List) ---
    master_frame = ttk.Frame(paned_window)
    paned_window.add(master_frame, weight=1) # Weight 1 gives it less space initially

    ttk.Label(
        master_frame, 
        text="Columns", 
        font=("TkDefaultFont", 10, "bold")
    ).pack(anchor="w", pady=(0, 5))

    # exportselection=False prevents the selection from clearing when clicking elsewhere
    columns_listbox = tk.Listbox(
        master_frame, 
        exportselection=False, 
        font=("TkDefaultFont", 10)
    )
    master_scroll = ttk.Scrollbar(
        master_frame, 
        orient="vertical", 
        command=columns_listbox.yview
    )
    
    columns_listbox.configure(yscrollcommand=master_scroll.set)
    columns_listbox.pack(
        side="left", 
        fill="both", 
        expand=True
    )
    master_scroll.pack(
        side="right", 
        fill="y"
    )

    # --- RIGHT PANE (Detail - Unique Values List) ---
    detail_frame = ttk.Frame(paned_window)
    paned_window.add(detail_frame, weight=2) # Weight 2 makes it twice as wide initially

    detail_label = ttk.Label(
        detail_frame, 
        text="Select a column to view values", 
        font=("TkDefaultFont", 10, "bold")
    )
    detail_label.pack(anchor="w", pady=(0, 5))

    values_listbox = tk.Listbox(
        detail_frame, 
        font=("TkDefaultFont", 10)
    )
    detail_scroll = ttk.Scrollbar(
        detail_frame, 
        orient="vertical", 
        command=values_listbox.yview
    )
    
    values_listbox.configure(yscrollcommand=detail_scroll.set)
    values_listbox.pack(
        side="left", 
        fill="both", 
        expand=True
    )
    detail_scroll.pack(
        side="right", 
        fill="y"
    )

    # --- WIRING IT TOGETHER ---
    
    unique_data = report.get("unique_values", {})

    # Populate the master listbox
    for col in unique_data.keys():
        columns_listbox.insert(tk.END, col)

    def on_column_select(event):
        selection = columns_listbox.curselection()
        if not selection:
            return
        
        # Get the selected column name
        selected_col = columns_listbox.get(selection[0])
        values = unique_data.get(selected_col, set())
        
        # Update the detail label to show count
        detail_label.config(text=f"Unique values for '{selected_col}' ({len(values)} total)")
        
        # Clear the old values from the right pane
        values_listbox.delete(0, tk.END)

        # Sort column values
        sorted_values = sorted(list(values), key=lambda x: str(x))

        # Populating the right pane with unique values, but if the column has high cardinality, we show a message instead
        if isinstance(values, str) and values == "High Cardinality":
            detail_label.config(text=f"Unique values for '{selected_col}'")
            values_listbox.insert(tk.END, "This column has high cardinality (>1,000 unique values).")
            values_listbox.insert(tk.END, "Values are hidden to conserve memory.")

        else:
            for val in sorted_values:
                values_listbox.insert(tk.END, str(val))

    # Bind the click event on the left listbox to the function above
    columns_listbox.bind("<<ListboxSelect>>", on_column_select)
    
    # Automatically select the first column so the right pane isn't empty on load
    if unique_data:
        columns_listbox.selection_set(0)
        on_column_select(None)

    # ========================================================
    # ADDITIONAL INFORMATION
    # ========================================================

    additional_frame = ttk.Frame(parent_frame)
    additional_frame.pack(
        fill="x",
        padx=10,
        pady=(0, 10)
    )

    empty_count = len(report.get("empty_columns", []))
    drift_count = len(report.get("type_drifts", {}))
    duplicate_count = report.get("duplicate_counts", 0)

    ttk.Label(
        additional_frame,
        text=(
            f"100% Empty columns: {empty_count}    |    "
            f"Columns with Type Drifts: {drift_count}    |    "
            f"Duplicate count: {duplicate_count}"
        )
    ).pack(side="left")

    ttk.Button(
        additional_frame,
        text="Close",
        command=parent_frame.destroy
    ).pack(side="right")


def select_file(
    row_size: int,
    view_method: str,
    filepath: str | None = None,
    parent_frame: ttk.Frame | None = None,
) -> None:

    if not filepath:
        filepath = filedialog.askopenfilename(
            filetypes=[
                ("All Spreadsheets", "*.csv *.xlsx *.xls"),
                ("CSV Files", "*.csv"),
                ("Excel Files", "*.xlsx *.xls")
            ]
        )

    if not filepath:
        logger.info("File selection cancelled by user")
        return

    logger.info("Loading preview rows=%s mode=%s file=%s", row_size, view_method, Path(filepath).name)

    extension = Path(filepath).suffix.lower()
    loading_parent = parent_frame or tk._default_root

    if loading_parent is None:
        raise RuntimeError("A Tkinter root is required to show loading feedback.")

    progress_win = tk.Toplevel(loading_parent)
    progress_win.title("Loading File")
    progress_win.geometry("300x120")
    progress_win.resizable(False, False)
    progress_win.transient(loading_parent.winfo_toplevel())
    progress_win.grab_set()

    ttk.Label(
        progress_win,
        text="Loading file...\nPlease wait.",
        justify="center",
    ).pack(pady=15)

    progress = ttk.Progressbar(progress_win, mode="indeterminate")
    progress.pack(fill="x", padx=20)
    progress.start()

    def close_progress() -> None:
        progress.stop()
        progress_win.grab_release()
        progress_win.destroy()

    def on_success(df: pd.DataFrame) -> None:
        close_progress()
        show_data(df, filepath)

    def on_error(error: str) -> None:
        close_progress()
        messagebox.showerror(
            "File Error",
            f"Could not load the file.\n\n{error}",
        )

    def count_rows_in_file(filepath: str) -> int:

        row_count = 0

        with open(filepath, "r", encoding="utf-8", errors="ignore") as file:
            if extension == ".csv":
                reader = csv.reader(file)
                row_count = sum(1 for _ in reader) 

            elif extension == ".xlsx":
                wb = load_workbook(filepath, read_only=True)
                ws = wb.active

                row_count = sum(1 for _ in ws.iter_rows(min_row=2)) 

            elif extension == ".xls":
                wb = xlrd.open_workbook(filepath)
                ws = wb.sheet_by_index(0)

                row_count = sum(1 for _ in ws.get_rows()) - 1 

            else:
                raise ValueError(f"Unsupported format: {extension}")

        return row_count

    def load_data() -> None:
        started_at = time.perf_counter()
        try:
            logger.info("Preview data load started for %s", Path(filepath).name)
            match extension:
                case ".csv":
                    if view_method == "head":
                        df = pd.read_csv(filepath, nrows=row_size + 1) # To accomodate header row for +1

                    elif view_method == "tail":
                        total_rows = count_rows_in_file(filepath)

                        df = pd.read_csv(
                            filepath,
                            skiprows=lambda x: x != 0 and x < total_rows - row_size
                        )

                    elif view_method == "random":
                        total_rows = count_rows_in_file(filepath)

                        if total_rows <= row_size:
                            df = pd.read_csv(filepath)
                        else:
                            random_indices = sorted(
                                random.sample(range(1, total_rows + 1), row_size)
                            )

                            df = pd.read_csv(
                                filepath,
                                skiprows=lambda x: x != 0 and x not in random_indices
                            )

                case ".xlsx" | ".xls":
                    if view_method == "head":
                        df = pd.read_excel(
                            filepath,
                            engine="calamine",
                            nrows=row_size + 1
                        )

                    elif view_method == "tail":
                        total_rows = count_rows_in_file(filepath)

                        df = pd.read_excel(
                            filepath,
                            engine="calamine",
                            skiprows=lambda x: x != 0 and x < total_rows - row_size
                        )

                    elif view_method == "random":
                        total_rows = count_rows_in_file(filepath)

                        if total_rows <= row_size:
                            df = pd.read_excel(filepath, engine="calamine")
                        else:
                            random_indices = sorted(
                                random.sample(range(1, total_rows + 1), row_size)
                            )

                            df = pd.read_excel(
                                filepath,
                                engine="calamine",
                                skiprows=lambda x: x != 0 and x not in random_indices
                            )

                case _:
                    raise ValueError("Please select a CSV, XLSX, or XLS file.")

            duration = time.perf_counter() - started_at
            logger.info(
                "Preview data load completed for %s in %.2fs (%s rows)",
                Path(filepath).name,
                duration,
                len(df),
            )
            loading_parent.after(0, lambda: on_success(df))
        except Exception as e:
            duration = time.perf_counter() - started_at
            logger.exception(
                "Preview data load failed after %.2fs for %s",
                duration,
                Path(filepath).name,
            )
            loading_parent.after(0, lambda error=str(e): on_error(error))

    threading.Thread(target=load_data, daemon=True).start()


def build_quality_checker_tab(parent_frame: ttk.Frame) -> None:

    parent_frame.columnconfigure(0, weight=1)
    parent_frame.rowconfigure(0, weight=1)

    # ========================================================
    # Options container
    # ========================================================
    options_container = ttk.Frame(parent_frame)
    options_container.pack(
        fill="both",
        expand=True,
        padx=10,
        pady=10
    )

    options_container.columnconfigure(0, weight=1)
    options_container.rowconfigure(0, weight=1)
    options_container.rowconfigure(1, weight=1)

    # ========================================================
    # Row input
    # ========================================================
    rows_frame = ttk.Frame(options_container)
    rows_frame.grid(
        row=0,
        column=0,
        sticky="n",
        pady=(15, 10),
    )

    rows_label = ttk.Label(
        rows_frame,
        text="Show rows:",
        font=("TkDefaultFont", 16, "bold"),
    )
    rows_label.pack(
        side="left",
        padx=(0, 10),
    )

    def validate_number_input(value: str) -> bool:
        return value == "" or (value.isdigit() and int(value) > 0)

    validate_cmd = (parent_frame.register(validate_number_input), "%P")

    rows_entry = ttk.Entry(
        rows_frame,
        width=20,
        validate="key",
        validatecommand=validate_cmd
    )
    rows_entry.insert(0, "500")
    rows_entry.pack(side="left")

    row_tooltip = ttk.Button(
        rows_frame,
        text="ⓘ",
        style="Toolbutton",
        cursor="hand2",
        command=lambda: messagebox.showinfo(
            "Row Input Information",
            "This input determines how many rows of the spreadsheet will be displayed in the preview table.\n\n"
            "Recommended: 500 rows\n\n"
            "You can increase this number if your system can handle it, but be cautious as very large numbers may slow down the application."
        )
    )
    row_tooltip.pack(
        side="left",
        padx=(5, 0),
    )   

    # ========================================================
    # Display Options
    # ========================================================

    display_options_frame = ttk.Frame(options_container)
    display_options_frame.grid(
        row=1,
        column=0,
        sticky="n",
        pady=(10, 15),
        padx=10,
    )

    display_options_text_frame = ttk.Frame(display_options_frame)
    display_options_text_frame.pack(
        pady=(0, 10),
    )

    display_options_label = ttk.Label(
        display_options_text_frame,
        text="Display Options:",
        font=("TkDefaultFont", 16, "bold"),
    )
    display_options_label.pack(side="left")

    display_options_tooltip = ttk.Button(
        display_options_text_frame,
        text="ⓘ",
        style="Toolbutton",
        cursor="hand2",
        command=lambda: messagebox.showinfo(
            "Display Options Information",
            "These options determine which rows of the spreadsheet will be displayed in the preview table.\n\n"
            "Show Head: Displays the first N rows of the spreadsheet.\n\n"
            "Show Tail: Displays the last N rows of the spreadsheet.\n\n"
            "Show Random: Displays N random rows from the spreadsheet."
        )
    )
    display_options_tooltip.pack(
        padx=(6, 0),
        side="left"
    )

    table_display_var = tk.StringVar(value="head")

    radio_frame = ttk.Frame(display_options_frame)
    radio_frame.pack(
        padx=10,
        pady=0,
    )

    show_head_button = ttk.Radiobutton(
        radio_frame,
        text="Show Head",
        value="head",
        variable=table_display_var,
        cursor="hand2"
    )
    show_head_button.pack(
        side="left",
        padx=(0, 12),
    )

    show_tail_button = ttk.Radiobutton(
        radio_frame,
        text="Show Tail",
        value="tail",
        variable=table_display_var,
        cursor="hand2"
    )
    show_tail_button.pack(
        side="left",
        padx=12,
    )

    show_random_button = ttk.Radiobutton(
        radio_frame,
        text="Show Random",
        value="random",
        variable=table_display_var,
        cursor="hand2"
    )
    show_random_button.pack(
        side="left",
        padx=(12, 0),
    )

    # ========================================================
    # File selection container
    # ========================================================
    file_select_container = ttk.Frame(parent_frame)
    file_select_container.pack(
        fill="both",
        expand=True,
        padx=10,
        pady=(0, 10)
    )

    canvas = tk.Canvas(
        file_select_container,
        highlightthickness=0,
        cursor="hand2",
    )
    canvas.pack(
        fill="both",
        expand=True,
    )

    rectangle = canvas.create_rectangle(
        2, 2, 2, 2, 
        outline="gray",
        width=2,
        dash=(8, 5),
    )

    image_parse = Image.open(os.path.join(ASSETS_DIR, "icons", "upload_icon.png"))
    image_parse = image_parse.resize((80, 80))
    upload_icon = ImageTk.PhotoImage(image_parse)

    canvas.upload_icon = upload_icon

    upload_image_id = canvas.create_image(
        0, 0,
        image=upload_icon,
    )

    upload_text_id = canvas.create_text(
        0, 0,
        text="Click to select a file",
        font=("TkDefaultFont", 14, "bold"),
        fill="black",
    )

    upload_subtext_id = canvas.create_text(
        0, 0,
        text="or drag and drop it here",
        font=("TkDefaultFont", 11),
        fill="gray",
    )


    def resize_drop_zone(event):
        width = event.width
        height = event.height

        canvas.coords(
            rectangle,
            2, 2, width - 2, height - 2,
        )

        center_x = width / 2
        center_y = height / 2

        canvas.coords(
            upload_image_id,
            center_x,
            center_y - 40   
        )
        canvas.coords(
            upload_text_id,
            center_x, 
            center_y + 20
        )
        canvas.coords(
            upload_subtext_id,
            center_x, 
            center_y + 45
        )

    canvas.bind("<Configure>", resize_drop_zone)

    def on_click(event) -> None:
        row_input = rows_entry.get().strip()
        if not row_input:
            logger.warning("Missing row input while selecting quality preview file")
            messagebox.showerror(
                "Missing Information", 
                "Row entry cannot be empty. Please enter a valid number."
            )
            return  
        
        select_file(
            int(row_input), 
            table_display_var.get(),
            parent_frame=parent_frame,
        )

    def on_drop(event):
        row_input = rows_entry.get().strip()
        if not row_input:
            logger.warning("Missing row input while dropping quality preview file")
            messagebox.showerror(
                "Missing Information", 
                "Row entry cannot be empty. Please enter a valid number."
            )
            return  
        
        filepaths = canvas.tk.splitlist(event.data)

        if len(filepaths) > 1:
            messagebox.showinfo(
                "File Dropped",
                f"You dropped multiple files.\n\n"
                f"Only the first file will be processed:\n\n"
                f"{filepaths[0]}"
            )

        filepath = filepaths[0]
        select_file(
            int(rows_entry.get()),
            table_display_var.get(),
            filepath,
            parent_frame=parent_frame,
        )

    canvas.bind("<Button-1>", on_click)
    canvas.drop_target_register(DND_FILES)
    canvas.dnd_bind("<<Drop>>", on_drop)