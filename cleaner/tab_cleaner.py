import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import pandas as pd
from nameparser import HumanName
from tkinterdnd2 import DND_FILES


def clean_dataframe(
    df: pd.DataFrame,
    trim_text: bool,
    fill_missing: str,
    strip_chars: str,
    column_transformations: dict,
) -> pd.DataFrame:
    
    cleaned = df

    # 1. Text Normalization
    if trim_text:
        str_cols = cleaned.select_dtypes(include="object").columns
        for col in str_cols:
            cleaned[col] = cleaned[col].astype("string").str.strip()

    # 2. Strip special characters
    if strip_chars:
        chars = strip_chars.split(",")
        object_columns = cleaned.select_dtypes(include="object").columns
        for col in object_columns:
            for char in chars:
                char = char.strip()
                if char:
                    cleaned[col] = cleaned[col].astype("string").str.replace(char, "", regex=False)

    # 3. Column-specific Text Case & Advanced Formatting
    # We create a list of columns to iterate over so we can safely add new columns inside the loop
    for col in list(column_transformations.keys()):
        transformation = column_transformations[col]

        # Prevert KeyError if the column is not present in the DataFrame or if the user selected "Keep Original"
        if col not in cleaned.columns or transformation == "Keep Original":
            continue

        if transformation == "lowercase":
            cleaned[col] = cleaned[col].astype("string").str.lower()

        elif transformation == "UPPERCASE":
            cleaned[col] = cleaned[col].astype("string").str.upper()

        elif transformation == "Title Case":
            cleaned[col] = cleaned[col].astype("string").str.title()

        # Used for cleaning up date formats, especially when users have inconsistent date formats in their dataset
        elif transformation == "Date (YYYY-MM-DD)":
            cleaned[col] = pd.to_datetime(cleaned[col], errors="coerce").dt.strftime("%Y-%m-%d")

        # Used for cleaning up phone numbers, IDs, or any other numeric-only fields
        elif transformation == "Numbers Only":
            cleaned[col] = cleaned[col].astype(str).str.replace(r"\D", "", regex=True)

        # Used for cleaning up currency values to just the numeric part, removing symbols like $, €, £, etc.
        elif transformation == "Clean Currency":
            cleaned[col] = cleaned[col].astype(str).str.replace(r"[^\d.-]", "", regex=True)
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")

        elif transformation == "Extract Email":
            # Extracts the first valid email format found in the text
            cleaned[col] = cleaned[col].astype(str).str.extract(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})')[0]

        elif transformation == "Extract URL":
            # Extracts the first valid web link found in the text
            cleaned[col] = cleaned[col].astype(str).str.extract(r'(https?://\S+|www\.\S+)')[0]

        elif transformation == "Anonymize Email":
            # Turns "john.doe@gmail.com" into "j***@gmail.com"
            cleaned[col] = cleaned[col].astype(str).str.replace(r'(?<=.).(?=.*@)', '*', regex=True)
            
        elif transformation == "Anonymize Numbers (Keep Last 4)":
            # Replaces all digits except the last 4 with asterisks (great for IDs/Credit Cards)
            cleaned[col] = cleaned[col].astype(str).str.replace(r'\d(?=\d{4})', '*', regex=True)

        elif transformation == "Split Human Names":
            # Parses names like "Dr. John W. Doe Jr." and creates two NEW columns next to it
            parsed_names = cleaned[col].astype(str).apply(lambda x: HumanName(x) if pd.notna(x) else None)
            
            col_idx = cleaned.columns.get_loc(col)
            # Insert First and Last name columns immediately after the original column
            cleaned.insert(col_idx + 1, f"{col} - First", parsed_names.apply(lambda x: x.first if x else ""))
            cleaned.insert(col_idx + 2, f"{col} - Last", parsed_names.apply(lambda x: x.last if x else ""))

    # 4. Missing Values
    if fill_missing == "Drop Rows":
        cleaned = cleaned.dropna()
    elif fill_missing == "Fill 'N/A'":
        cleaned = cleaned.fillna("N/A")

    return cleaned


def build_cleaner_tab(parent_frame: ttk.Frame) -> None:
    
    loaded_file = {
        "path": "",
        "columns": []
    }

    column_transformations = dict()

    parent_frame.columnconfigure(0, weight=1)
    parent_frame.rowconfigure(1, weight=1)

    # Top Control Bar
    top_bar = ttk.Frame(parent_frame, padding=10)
    top_bar.grid(row=0, column=0, sticky="ew")

    file_label = ttk.Label(
        top_bar,
        text="Drag & Drop a CSV or Excel file here",
        padding=(10, 0),
        font=("TkDefaultFont", 10, "bold")
    )

    def load_file(filepath: str | None = None) -> None:
        if not filepath:
            filepath = filedialog.askopenfilename(
                title="Select Spreadsheet",
                filetypes=[
                    ("All Spreadsheets", "*.csv *.xlsx *.xls"),
                    ("CSV Files", "*.csv"),
                    ("Excel Files", "*.xlsx *.xls")
                ]
            )

        if not filepath:
            return

        extension = Path(filepath).suffix.lower()

        # Optimization: Read dataset headings only instead of reading everything
        try:
            if extension == ".csv":
                columns = pd.read_csv(filepath, nrows=0).columns.tolist()

            elif extension in [".xlsx", ".xls"]:
                columns = pd.read_excel(filepath, engine="calamine", nrows=0).columns.tolist()

            else:
                messagebox.showwarning("Invalid File", "Please select a CSV or Excel file.")
                return
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read file headers:\n{e!s}")
            return

        loaded_file["columns"] = columns
        loaded_file["path"] = filepath

        file_label.config(
            text=f"Loaded: {Path(filepath).name} ({len(columns):,} columns)"
        )
        file_label.pack(side="left")

    def select_column_transformations() -> None:
        if not loaded_file["columns"]:
            messagebox.showwarning("Warning", "Please select a file first.")
            return

        transformation_window = tk.Toplevel(parent_frame)
        transformation_window.title("Column Transformations")
        transformation_window.geometry("600x450")
        transformation_window.minsize(450, 300)

        ttk.Label(
            transformation_window,
            text="Select a transformation for each column:",
            font=("TkDefaultFont", 10, "bold")
        ).pack(anchor="w", padx=10, pady=10)

        columns_container = ttk.Frame(transformation_window)
        columns_container.pack(fill="both", expand=True, padx=10)

        columns_container.columnconfigure(0, weight=1)
        columns_container.rowconfigure(0, weight=1)

        # Canvas provides the scrolling area
        canvas = tk.Canvas(columns_container, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")

        # Vertical scrollbar
        v_scrollbar = ttk.Scrollbar(columns_container, orient="vertical", command=canvas.yview)
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=v_scrollbar.set)

        # Frame that will contain the column rows
        columns_frame = ttk.Frame(canvas)

        # Put the frame inside the canvas
        canvas_window = canvas.create_window((0, 0), window=columns_frame, anchor="nw")

        # Update scrolling area when the column frame changes size
        def update_scroll_region(event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        columns_frame.bind("<Configure>", update_scroll_region)

        # Make the column frame match the width of the canvas
        def update_canvas_width(event) -> None:
            canvas.itemconfigure(canvas_window, width=event.width)

        canvas.bind("<Configure>", update_canvas_width)

        # ----- Mouse Wheel Scrolling -----
        def on_mousewheel(event):
            if event.num == 4:          # Linux scroll up
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:        # Linux scroll down
                canvas.yview_scroll(1, "units")
            elif event.delta:           # Windows
                canvas.yview_scroll(int(-event.delta / 120), "units")

        def bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", on_mousewheel)
            canvas.bind_all("<Button-4>", on_mousewheel)
            canvas.bind_all("<Button-5>", on_mousewheel)

        def unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        # Fix canvas detecting mouse scroll due to main_container blockage
        canvas.bind("<Enter>", bind_mousewheel)
        canvas.bind("<Leave>", unbind_mousewheel)

        # Temporary storage while user is selecting changes to each column.
        transformation_vars = {}

        for column in loaded_file["columns"]:
            # Each column gets its own frame
            row = ttk.Frame(columns_frame)
            row.pack(fill="x", pady=3)

            ttk.Label(row, text=str(column), width=25).pack(side="left")

            var = tk.StringVar(
                value=column_transformations.get(column, "Keep Original")
            )
            transformation_vars[column] = var

            # Updated with new powerful formatting tools
            ttk.Combobox(
                row,
                textvariable=var,
                values=[
                    "Keep Original",
                    "lowercase",
                    "UPPERCASE",
                    "Title Case",
                    "Date (YYYY-MM-DD)",
                    "Numbers Only",
                    "Clean Currency",
                    "Extract Email",
                    "Extract URL",
                    "Anonymize Email",
                    "Anonymize Numbers (Keep Last 4)",
                    "Split Human Names",
                ],
                state="readonly",
                width=24
            ).pack(side="right")

        def apply_transformations():
            # Clean current column transformation dictionary
            column_transformations.clear()
            # Update each columns with their new values
            for column, var in transformation_vars.items():
                column_transformations[column] = var.get()
            transformation_window.destroy()

        ttk.Button(
            transformation_window, 
            text="Apply", 
            cursor="hand2",
            command=apply_transformations
        ).pack(pady=10)

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
        cursor="hand2",
        command=load_file
    )
    select_btn.pack(side="left")
    file_label.pack(side="left", padx=(10, 0))

    # Allow files to be dropped on whole frame of tab_cleaner section
    parent_frame.drop_target_register(DND_FILES)
    parent_frame.dnd_bind("<<Drop>>", on_drop)

    # Options Frame
    options_frame = ttk.LabelFrame(
        parent_frame, 
        text="Cleaning Transformations", 
        padding=12
    )
    options_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    var_dupes = tk.BooleanVar(value=True)
    var_trim = tk.BooleanVar(value=True)
    var_missing = tk.StringVar(value="Keep Missing")
    var_strip = tk.StringVar(value="$, ₱, %")

    ttk.Checkbutton(
        options_frame, 
        text="Remove Duplicate Rows", 
        variable=var_dupes,
        cursor="hand2"
    ).pack(anchor="w", pady=4)
    
    ttk.Checkbutton(
        options_frame, 
        text="Trim Whitespace from All Text Columns", 
        variable=var_trim,
        cursor="hand2"
    ).pack(anchor="w", pady=4)

    missing_row = ttk.Frame(options_frame)
    missing_row.pack(anchor="w", pady=6)
    
    ttk.Label(
        missing_row, 
        text="Handle Missing Values:",
        font=("TkDefaultFont", 9, "bold")
    ).pack(side="left", padx=(0, 6))
    
    ttk.Combobox(
        missing_row, 
        textvariable=var_missing, 
        values=["Keep Missing", "Drop Rows", "Fill 'N/A'"], 
        state="readonly",
        cursor="hand2"
    ).pack(side="left")

    strip_row = ttk.Frame(options_frame)
    strip_row.pack(anchor="w", pady=6)
    
    ttk.Label(
        strip_row, 
        text="Strip Characters (comma-separated):",
        font=("TkDefaultFont", 9, "bold")
    ).pack(side="left", padx=(0, 6))
    
    ttk.Entry(strip_row, textvariable=var_strip, width=15).pack(side="left")

    ttk.Button(
        options_frame, 
        text="Select Column Transformations", 
        cursor="hand2",
        command=select_column_transformations
    ).pack(anchor="w", pady=12)

    # ==========================================
    # BACKGROUND EXPORT LOGIC
    # ==========================================
    def export_clean() -> None:
        if not loaded_file.get("path"):
            messagebox.showwarning("Warning", "Please select a file first.")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv", 
            filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx")]
        )

        if not save_path:
            return

        # 1. Grab all UI variable states BEFORE launching the thread (Tkinter isn't thread-safe)
        dupes_val = var_dupes.get()
        trim_val = var_trim.get()
        missing_val = var_missing.get()
        strip_val = var_strip.get()
        file_path = loaded_file["path"]
        transforms_copy = column_transformations.copy()

        # 2. Show a progress popup so the user knows it hasn't frozen
        progress_win = tk.Toplevel(parent_frame)
        progress_win.title("Exporting...")
        
        # Center the progress window on the screen
        window_width, window_height = 300, 120
        screen_width = progress_win.winfo_screenwidth()
        screen_height = progress_win.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        progress_win.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        progress_win.transient(parent_frame.winfo_toplevel())
        progress_win.grab_set()

        ttk.Label(
            progress_win, 
            text="Processing data in the background...\nPlease wait.",
            justify="center"
        ).pack(pady=15)
        
        progress = ttk.Progressbar(progress_win, mode="indeterminate")
        progress.pack(fill="x", padx=20)
        progress.start()

        # 3. The actual processing logic (runs in background)
        def process_data_thread():
            try:
                extension = Path(file_path).suffix.lower()
                save_is_csv = Path(save_path).suffix.lower() == ".csv"
                is_csv = extension == ".csv"
                
                total_rows = 0
                seen_hashes = set() # Global Hash Set for chunk deduplication

                if is_csv and save_is_csv:
                    # Optimized Chunking for CSV -> CSV
                    first_chunk = True
                    for chunk in pd.read_csv(file_path, chunksize=50000):
                        
                        cleaned_chunk = clean_dataframe(
                            df=chunk, 
                            trim_text=trim_val, 
                            fill_missing=missing_val, 
                            strip_chars=strip_val, 
                            column_transformations=transforms_copy
                        )

                        # Global Deduplication Logic
                        if dupes_val:
                            cleaned_chunk = cleaned_chunk.drop_duplicates()
                            
                            # Hash each row into a compact 64-bit unsigned integer.
                            # Makes it much faster to check for duplicates across chunks instead of comparing entire rows
                            # This lets us efficiently detect duplicates across chunks
                            # without storing/comparing entire rows.
                            row_hashes = pd.util.hash_pandas_object(cleaned_chunk, index=False)
                            
                            # Keep rows whose hash isn't in our global set yet
                            # Tilde (~) operator inverts the boolean mask, so we keep rows that are NOT in seen_hashes
                            mask = ~row_hashes.isin(seen_hashes)
                            cleaned_chunk = cleaned_chunk[mask] # This is boolean filtering, don't get confused
                            
                            # Update the global set for the next chunks
                            seen_hashes.update(row_hashes[mask])

                        total_rows += len(cleaned_chunk)

                        cleaned_chunk.to_csv(
                            save_path, 
                            mode='a' if not first_chunk else 'w', 
                            header=first_chunk, 
                            index=False
                        )
                        first_chunk = False
                else:
                    # Fallback for Excel files (Pandas requires loading the whole file)
                    # Use Calamine engine for massive read speed upgrades
                    # NOTE: This will load the entire dataset into memory, so it may not be suitable for very large Excel files and saving to Excel. For large datasets, CSV is recommended.
                    df = pd.read_excel(file_path, engine="calamine") if not is_csv else pd.read_csv(file_path)
                    
                    cleaned = clean_dataframe(
                        df, 
                        trim_text=trim_val, 
                        fill_missing=missing_val, 
                        strip_chars=strip_val, 
                        column_transformations=transforms_copy
                    )

                    if dupes_val:
                        cleaned = cleaned.drop_duplicates()
                    
                    total_rows = len(cleaned)

                    if save_is_csv:
                        cleaned.to_csv(save_path, index=False)
                    else:
                        cleaned.to_excel(save_path, index=False)

                # 4. Safely update the GUI when finished
                parent_frame.after(0, lambda: on_success(total_rows))

            except Exception as e:
                # Safely update GUI on error
                parent_frame.after(0, lambda error=str(e): on_error(error))

        # Callbacks to handle the thread finishing
        def on_success(rows):
            progress_win.destroy()
            messagebox.showinfo("Success", f"Cleaned dataset saved ({rows:,} rows remaining).")

        def on_error(err_msg):
            progress_win.destroy()
            messagebox.showerror("Error", f"Failed during export:\n{err_msg}")

        # 5. Start the thread!
        thread = threading.Thread(target=process_data_thread, daemon=True)
        thread.start()

    ttk.Button(
        parent_frame, 
        text="Apply Cleaning & Export File", 
        cursor="hand2",
        command=export_clean
    ).grid(row=2, column=0, pady=10, ipady=4)