import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import pandas as pd
from tkinterdnd2 import DND_FILES

from quality.quality_checker import check_quality


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

    number_of_rows = 10 # to access updating variable at the bottom

    rows_text = tk.StringVar(value=f"Rows: {number_of_rows:,}    Columns: {len(df.columns)}")

    size_label = ttk.Label(
        info_frame,
        textvariable=rows_text,
        font=("TkDefaultFont", 12, "bold")
    )
    size_label.pack(side="right")

    # ----- Row input -----

    row_frame = ttk.Frame(parent_frame)
    row_frame.pack(
        fill="x",
        padx=10,
        pady=(0, 10)
    )

    ttk.Label(
        row_frame,
        text="Show rows:"
    ).pack(side="left")

    row_entry = ttk.Entry(
        row_frame,
        width=10
    )

    row_entry.insert(0, "10")
    row_entry.pack(
        side="left",
        padx=(5, 5)
    )

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
            width=120,
            anchor="w"
        )

    # ----- Function to update table -----

    def update_table():

        try:
            number_of_rows = int(row_entry.get())

            if number_of_rows <= 0:
                messagebox.showerror(
                    "Invalid Number",
                    "Please enter a number greater than 0."
                )
                return

            if number_of_rows > len(df):
                messagebox.showwarning(
                    "Too Many Rows",
                    f"The file only contains {len(df):,} rows.\n\n"
                    f"The table will show all available rows."
                )

            number_of_rows = min(
                number_of_rows,
                len(df)
            )

            # Update information at the top
            rows_text.set(
                f"Rows: {number_of_rows:,}    "
                f"Columns: {len(df.columns):,}"
            )

            # Remove existing rows
            tree.delete(*tree.get_children())

            # Insert new rows
            for row in df.head(
                number_of_rows
            ).itertuples(
                index=False,
                name=None
            ):
                tree.insert(
                    "",
                    "end",
                    values=row
                )

        except ValueError:
            messagebox.showerror(
                "Invalid Input",
                "Please enter a whole number.\n\n"
                "Example: 100, 500, or 1000"
            )

        except Exception as error:
            messagebox.showerror(
                "Table Update Error",
                f"Could not update the table.\n\n{error}"
            )

    update_button = ttk.Button(
        row_frame,
        text="Update",
        command=update_table
    )
    update_button.pack(side="left")

    # Add keybinds when updating table (Enter to update table)
    # event is needed since tkinter usually gives event attributes
    row_entry.bind("<Return>", lambda event: update_table())

    # ----- Initial table -----

    update_table()

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

    table_frame.rowconfigure(
        0,
        weight=1
    )

    table_frame.columnconfigure(
        0,
        weight=1
    )

    # ----- Quality button -----

    def open_quality_report():
        report = check_quality(df)
        show_quality_report(report)

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

    # --------------------------------------------------------
    # Helper function for metric cards
    # --------------------------------------------------------

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

    basic_info = report["basic_info"]

    create_card(
        cards_frame,
        "ROWS",
        f"{basic_info['rows']:,}",
        0
    )

    create_card(
        cards_frame,
        "COLUMNS",
        f"{basic_info['columns']:,}",
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
            "non_null",
            "missing",
            "missing_percentage",
            "unique",
            "is_constant",
            "is_empty"
        ),
        show="headings"
    )

    columns_tree.heading(
        "column",
        text="Column"
    )

    columns_tree.heading(
        "dtype",
        text="Data Type"
    )

    columns_tree.heading(
        "non_null",
        text="Non-Null"
    )

    columns_tree.heading(
        "missing",
        text="Missing"
    )

    columns_tree.heading(
        "missing_percentage",
        text="Missing %"
    )

    columns_tree.heading(
        "unique",
        text="Unique"
    )

    columns_tree.heading(
        "is_constant",
        text="Constant?"
    )

    columns_tree.heading(
        "is_empty",
        text="Empty?"
    )

    columns_tree.column(
        "column",
        width=180
    )

    columns_tree.column(
        "dtype",
        width=100
    )

    columns_tree.column(
        "non_null",
        width=100,
        anchor="center"
    )

    columns_tree.column(
        "missing",
        width=100,
        anchor="center"
    )

    columns_tree.column(
        "missing_percentage",
        width=110,
        anchor="center"
    )

    columns_tree.column(
        "unique",
        width=100,
        anchor="center"
    )

    columns_tree.column(
        "is_constant",
        width=100,
        anchor="center"
    )

    columns_tree.column(
        "is_empty",
        width=100,
        anchor="center"
    )

    horizontal_scrollbar = ttk.Scrollbar(
        columns_tab,
        orient="horizontal",
        command=columns_tree.xview
    )

    vertical_scrollbar = ttk.Scrollbar(
        columns_tab,
        orient="vertical",
        command=columns_tree.yview
    )

    columns_tree.configure(
        xscrollcommand=horizontal_scrollbar.set,
        yscrollcommand=vertical_scrollbar.set
    )

    columns_tree.grid(
        row=0,
        column=0,
        sticky="nsew"
    )

    horizontal_scrollbar.grid(
        row=1,
        column=0,
        sticky="ew"
    )

    vertical_scrollbar.grid(
        row=0,
        column=1,
        sticky="ns"
    )

    columns_tab.rowconfigure(0, weight=1)
    columns_tab.columnconfigure(0, weight=1)

    # ----- Populate columns table -----

    for column, info in report["columns"].items():

        columns_tree.insert(
            "",
            "end",
            values=(
                column,
                info["dtype"],
                f"{info['non_null']:,}",
                f"{info['missing']:,}",
                f"{info['missing_percentage']:.2f}%",
                f"{info['unique']:,}",
                info["is_empty"],
                info["is_constant"]
            )
        )

    # ========================================================
    # MISSING VALUES TAB
    # ========================================================

    missing_tab = ttk.Frame(notebook)
    notebook.add(
        missing_tab,
        text="Missing Values"
    )

    missing_tree = ttk.Treeview(
        missing_tab,
        columns=(
            "column",
            "count",
            "percentage"
        ),
        show="headings"
    )

    missing_tree.heading(
        "column",
        text="Column"
    )

    missing_tree.heading(
        "count",
        text="Missing Count"
    )

    missing_tree.heading(
        "percentage",
        text="Missing %"
    )

    missing_tree.column(
        "column",
        width=250
    )

    missing_tree.column(
        "count",
        width=150,
        anchor="center"
    )

    missing_tree.column(
        "percentage",
        width=150,
        anchor="center"
    )

    missing_scrollbar = ttk.Scrollbar(
        missing_tab,
        orient="vertical",
        command=missing_tree.yview
    )

    missing_tree.configure(
        yscrollcommand=missing_scrollbar.set
    )

    missing_tree.pack(
        side="left",
        fill="both",
        expand=True
    )

    missing_scrollbar.pack(
        side="right",
        fill="y"
    )

    # ----- Populate missing table -----

    for column, info in report["missing_values"]["by_column"].items():

        missing_tree.insert(
            "",
            "end",
            values=(
                column,
                f"{info['count']:,}",
                f"{info['percentage']:.2f}%"
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

    statistics = report["statistics"]

    if statistics:

        statistic_columns = [
            "column",
            "count",
            "mean",
            "std",
            "min",
            "25%",
            "50%",
            "75%",
            "max"
        ]

        statistics_tree = ttk.Treeview(
            statistics_tab,
            columns=statistic_columns,
            show="headings"
        )

        for column in statistic_columns:
            statistics_tree.heading(
                column,
                text=column
            )

            statistics_tree.column(
                column,
                width=100,
                anchor="center"
            )

        statistics_scrollbar = ttk.Scrollbar(
            statistics_tab,
            orient="vertical",
            command=statistics_tree.yview
        )

        statistics_horizontal = ttk.Scrollbar(
            statistics_tab,
            orient="horizontal",
            command=statistics_tree.xview
        )

        statistics_tree.configure(
            yscrollcommand=statistics_scrollbar.set,
            xscrollcommand=statistics_horizontal.set
        )

        statistics_tree.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        statistics_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        statistics_horizontal.grid(
            row=1,
            column=0,
            sticky="ew"
        )

        statistics_tab.rowconfigure(
            0,
            weight=1
        )

        statistics_tab.columnconfigure(
            0,
            weight=1
        )

        # ----- Populate statistics -----

        for column, values in statistics.items():

            statistics_tree.insert(
                "",
                "end",
                values=(
                    column,
                    f"{values.get('count', 0):,.2f}",
                    f"{values.get('mean', 0):,.2f}",
                    f"{values.get('std', 0):,.2f}",
                    f"{values.get('min', 0):,.2f}",
                    f"{values.get('25%', 0):,.2f}",
                    f"{values.get('50%', 0):,.2f}",
                    f"{values.get('75%', 0):,.2f}",
                    f"{values.get('max', 0):,.2f}"
                )
            )

    else:

        ttk.Label(
            statistics_tab,
            text="No numerical columns available.",
            font=("TkDefaultFont", 11)
        ).pack(pady=30)

    # ========================================================
    # ADDITIONAL INFORMATION
    # ========================================================

    additional_frame = ttk.Frame(parent_frame)
    additional_frame.pack(
        fill="x",
        padx=10,
        pady=(0, 10)
    )

    duplicate_count = report["duplicates"]["count"]

    empty_count = len(report["empty_columns"])
    constant_count = len(report["constant_columns"])

    ttk.Label(
        additional_frame,
        text=(
            f"Duplicate rows: {duplicate_count}    |    "
            f"Empty columns: {empty_count}    |    "
            f"Constant columns: {constant_count}"
        )
    ).pack(side="left")

    ttk.Button(
        additional_frame,
        text="Close",
        command=parent_frame.destroy
    ).pack(side="right")


def select_file(filepath: str = None) -> None:

    if not filepath:
        filepath = filedialog.askopenfilename(
            filetypes=[
                ("All Spreadsheets", "*.csv *.xlsx *.xls"),
                ("CSV Files", "*.csv"),
                ("Excel Files", "*.xlsx *.xls")
            ]
        )

    if not filepath:
        return

    extension = Path(filepath).suffix.lower()

    try:
        if extension == ".csv":
            df = pd.read_csv(filepath)

        elif extension == ".xlsx":
            df = pd.read_excel(filepath)

        else:
            messagebox.showerror(
                "Unsupported File",
                "Please select a CSV or XLSX file."
            )
            return

    except Exception as error:
        messagebox.showerror(
            "File Error",
            f"Could not load the file.\n\n{error}"
        )
        return

    show_data(df, filepath)


def build_quality_checker_tab(parent_frame: ttk.Frame) -> None:

    parent_frame.columnconfigure(0, weight=1)
    parent_frame.rowconfigure(0, weight=1)

    container = ttk.Frame(parent_frame)
    container.grid(row=0, column=0)

    def on_drop(event) -> None:
        file = parent_frame.tk.splitlist(event.data)

        if len(file) > 1:
            messagebox.showinfo(
                "Multiple Files Detected",
                f"Loading '{Path(file[0]).name}'. Multiple file batch cleaning is not supported on this tab."
            )

        # Load the first file in the list if multiple files are dropped
        select_file(file[0])

    parent_frame.drop_target_register(DND_FILES)
    parent_frame.dnd_bind("<<Drop>>", on_drop)

    ttk.Label(
        container,
        text="Drag and drop a spreadsheet here, or click below to browse",
        justify="center",
        font=("TkDefaultFont", 12, "bold")
    ).pack(pady=(0, 10))

    ttk.Button(
        container,
        text="Select file",
        command=select_file
    ).pack(ipady=4, ipadx=10)