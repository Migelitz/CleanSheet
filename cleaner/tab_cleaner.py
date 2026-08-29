import pandas as pd
import tkinter as tk

from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES

def clean_dataframe(
    df: pd.DataFrame,
    drop_dupes: bool,
    trim_text: bool,
    fill_missing: str,
    strip_chars: str,
    column_transformations: dict,
) -> pd.DataFrame:
    
    cleaned = df.copy()

    # 1. Deduplication
    if drop_dupes:
        cleaned = cleaned.drop_duplicates()

    # 2. Text Normalization
    if trim_text:
        str_cols = cleaned.select_dtypes(include="object").columns
        for col in str_cols:
            cleaned[col] = cleaned[col].astype("string").str.strip()

    # 3. Strip special characters (e.g. $, ₱, %)
    if strip_chars:
        chars = strip_chars.split(",")

        object_columns = cleaned.select_dtypes(include="object").columns

        for col in object_columns:
            for char in chars:
                char = char.strip()

                if char:
                    cleaned[col] = (
                        cleaned[col]
                        .astype("string")
                        .str.replace(char, "", regex=False)
                    )

    # 4. Column-specific Text Case
    for col, transformation in column_transformations.items():

        if col not in cleaned.columns:
            continue

        if transformation == "lowercase":
            cleaned[col] = cleaned[col].astype("string").str.lower()

        elif transformation == "UPPERCASE":
            cleaned[col] = cleaned[col].astype("string").str.upper()

        elif transformation == "Title Case":
            cleaned[col] = cleaned[col].astype("string").str.title()

    # 5. Missing Values
    if fill_missing == "Drop Rows":
        cleaned = cleaned.dropna()
    elif fill_missing == "Fill 'N/A'":
        cleaned = cleaned.fillna("N/A")

    return cleaned


def build_cleaner_tab(parent_frame: ttk.Frame) -> None:
    
    loaded_df = {"data": None, "path": ""}

    column_transformations = dict()

    parent_frame.columnconfigure(0, weight=1)
    parent_frame.rowconfigure(1, weight=1)

    # Top Control Bar
    top_bar = ttk.Frame(parent_frame, padding=10)
    top_bar.grid(
        row=0,
        column=0,
        sticky="ew"
    )

    file_label = ttk.Label(
        top_bar,
        text="Drag & Drop a CSV or Excel file here",
        padding=(10, 0)
    )

    # .pack() is at the bottom for proper arrangement

    def load_file(filepath: str | None = None) -> None:

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

        if extension == ".csv":
                df = pd.read_csv(filepath, chunksize=100_000)

        elif extension in [".xlsx", ".xls"]:
            df = pd.read_excel(filepath)

        else:
            messagebox.showwarning(
                "Invalid File",
                "Please select a CSV or Excel file."
            )
            return

        loaded_df["data"] = df
        loaded_df["path"] = filepath

        file_label.config(
            text=f"Loaded: {Path(filepath).name} ({len(df):,} rows)"
        )
        file_label.pack(side="left")

    def select_column_transformations() -> None:
        if loaded_df["data"] is None:
            messagebox.showwarning(
                "Warning",
                "Please select a file first."
            )
            return

        transformation_window = tk.Toplevel(parent_frame)
        transformation_window.title("Column Transformations")
        transformation_window.geometry("600x450")
        transformation_window.minsize(450,300)

        ttk.Label(
            transformation_window,
            text="Select a transformation for each column:",
            font=("TkDefaultFont", 12, "bold")
        ).pack(
            anchor="w",
            padx=10,
            pady=10
        )

        columns_container = ttk.Frame(transformation_window)

        columns_container.pack(
            fill="both",
            expand=True,
            padx=10
        )

        columns_container.columnconfigure(0, weight=1)
        columns_container.rowconfigure(0, weight=1)

        # Canvas provides the scrolling area
        canvas = tk.Canvas(
            columns_container,
            highlightthickness=0
        )

        canvas.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        # Vertical scrollbar
        scrollbar = ttk.Scrollbar(
            columns_container,
            orient="vertical",
            command=canvas.yview
        )

        scrollbar.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        canvas.configure(
            yscrollcommand=scrollbar.set
        )

        # Frame that will contain the column rows
        columns_frame = ttk.Frame(canvas)

        # Put the frame inside the canvas
        canvas_window = canvas.create_window(
            (0, 0),
            window=columns_frame,
            anchor="nw"
        )

        # Update scrolling area when the column frame changes size
        def update_scroll_region(event) -> None:
            canvas.configure(
                scrollregion=canvas.bbox("all")
            )

        columns_frame.bind("<Configure>", update_scroll_region)

        # Make the column frame match the width of the canvas
        def update_canvas_width(event) -> None:
            canvas.itemconfigure(
                canvas_window,
                width=event.width
            )

        canvas.bind("<Configure>", update_canvas_width)

        def on_mousewheel(event) -> None:
            canvas.yview_scroll(
                int(-1 * (event.delta / 120)),
                "units"
            )

        canvas.bind_all("<MouseWheel>", on_mousewheel)

        # Temporary storage while user is selecting changes to each column. Later apply changes to column_transformation dictionary
        # Stores all columns in their default values from for loop below for the first time
        transformation_vars = {}

        for column in loaded_df["data"].columns:
            # Each columns get own frame
            row = ttk.Frame(columns_frame)
            row.pack(
                fill="x",
                pady=3
            )

            ttk.Label(
                row,
                text=str(column),
                width=25
            ).pack(side="left")

            var = tk.StringVar(
                # .get() is dict function where first arg is the key and second args is default value if non-existent
                value=column_transformations.get(
                    column,
                    "Keep Original"
                )
            )

            transformation_vars[column] = var

            ttk.Combobox(
                row,
                textvariable=var,
                values=[
                    "Keep Original",
                    "lowercase",
                    "UPPERCASE",
                    "Title Case"
                ],
                state="readonly",
                width=18
            ).pack(side="left")

        def apply_transformations():
            # Clean current column transformation dictionary
            column_transformations.clear()

            # Update each columns with their new values (Like Title Case, UPPERCASE, or lowercase)
            for column, var in transformation_vars.items():
                column_transformations[column] = var.get()

            transformation_window.destroy()

        ttk.Button(
            transformation_window,
            text="Apply",
            command=apply_transformations
        ).pack(
            pady=10
        )

    # ===== END OF select_column_tranformation() FUNCTION =====

    def on_drop(event) -> None:
        file = parent_frame.tk.splitlist(event.data)

        if len(file) > 1:
            messagebox.showinfo(
                "Multiple Files Detected",
                f"Loading '{Path(file[0]).name}'. Multiple file batch cleaning is not supported on this tab."
            )

        # Load the first file in the list if multiple files are dropped
        load_file(file[0])

    select_btn = ttk.Button(
        top_bar,
        text="Select File to Clean",
        command=load_file
    )
    select_btn.pack(side="left")
    file_label.pack(side="left")

    # Allow files to be dropped on whole frame of tab_cleaner section
    parent_frame.drop_target_register(DND_FILES)
    parent_frame.dnd_bind("<<Drop>>", on_drop)

    # Options Frame
    options_frame = ttk.LabelFrame(
        parent_frame,
        text="Cleaning Transformations",
        padding=12
    )

    options_frame.grid(
        row=1,
        column=0,
        sticky="nsew",
        padx=10,
        pady=(0, 10)
    )

    var_dupes = tk.BooleanVar(value=True)
    var_trim = tk.BooleanVar(value=True)
    var_missing = tk.StringVar(value="Keep Missing")
    var_strip = tk.StringVar(value="$, ₱, %")

    ttk.Checkbutton(
        options_frame,
        text="Remove Duplicate Rows",
        variable=var_dupes
    ).pack(anchor="w", pady=4)

    ttk.Checkbutton(
        options_frame,
        text="Trim Whitespace from All Text Columns",
        variable=var_trim
    ).pack(anchor="w", pady=4)

    missing_row = ttk.Frame(options_frame)
    missing_row.pack(anchor="w", pady=6)

    ttk.Label(
        missing_row,
        text="Handle Missing Values:"
    ).pack(side="left", padx=(0, 6))

    ttk.Combobox(
        missing_row,
        textvariable=var_missing, 
        values=["Keep Missing", "Drop Rows", "Fill 'N/A'"], 
        state="readonly"
    ).pack(side="left")

    strip_row = ttk.Frame(options_frame)
    strip_row.pack(anchor="w", pady=6)

    ttk.Label(
        strip_row, 
        text="Strip Characters (comma-separated):"
    ).pack(side="left", padx=(0, 6))

    ttk.Entry(
        strip_row,
        textvariable=var_strip, 
        width=15
    ).pack(side="left")

    ttk.Button(
        options_frame,
        text="Select Column Transformations",
        command=select_column_transformations
    ).pack(
        anchor="w",
        pady=8
    )

    # Export Action
    def export_clean():

        if loaded_df["data"] is None:
            messagebox.showwarning("Warning", "Please select a file first.")
            return
        
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx")])

        if not save_path:
            return

        result = clean_dataframe(
            df=loaded_df["data"],
            drop_dupes=var_dupes.get(),
            trim_text=var_trim.get(),
            fill_missing=var_missing.get(),
            strip_chars=var_strip.get(),
            column_transformations=column_transformations,
        )

        if Path(save_path).suffix.lower() in [".xlsx", ".xls"]:
            result.to_excel(save_path, index=False)
        else:
            result.to_csv(save_path, index=False)

        messagebox.showinfo("Success", f"Cleaned dataset saved ({len(result):,} rows remaining).")

    ttk.Button(parent_frame, text="Apply Cleaning & Export File", command=export_clean).grid(row=2, column=0, pady=10, ipady=4)