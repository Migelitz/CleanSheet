import pandas as pd
import tkinter as tk

from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES


# ========================================================
# DATA PROCESSING FUNCTIONS
# ========================================================


def read_file(filepath: str) -> pd.DataFrame:
    """Reads a CSV or Excel file into a pandas DataFrame."""
    extension = Path(filepath).suffix.lower()

    if extension == ".csv":
        return pd.read_csv(filepath)

    elif extension in [".xlsx", ".xls"]:
        return pd.read_excel(filepath)

    else:
        raise ValueError(f"Unsupported format: {extension}")


def concat_files(
    files: list[str], output_folder: str, output_filename: str
) -> None:
    """Merges all files and saves them to the specified directory."""
    if not files:
        messagebox.showwarning(
            "No Files Selected", "Please select at least one file to merge."
        )
        return

    folder_path = Path(output_folder.strip())

    if not folder_path.exists() or not folder_path.is_dir():
        messagebox.showerror(
            "Invalid Folder",
            "The selected destination folder does not exist.\n\n"
            "Please choose a valid directory.",
        )
        return

    clean_filename = output_filename.strip()

    if not clean_filename:
        clean_filename = "merged_spreadsheet.csv"

    output_path = folder_path / clean_filename
    extension = output_path.suffix.lower()

    try:
        # Load and combine all datasets
        merged_df = pd.concat(
            (read_file(filepath) for filepath in files), ignore_index=True
        )

        # Determine export format
        if extension in [".xlsx", ".xls"]:
            merged_df.to_excel(
                output_path,
                index=False,
            )

        else:
            if extension != ".csv":
                output_path = output_path.with_suffix(".csv")

            merged_df.to_csv(
                output_path,
                index=False,
            )

        messagebox.showinfo(
            "Success",
            f"Successfully merged {len(files)} files into:\n{output_path.resolve()}",
        )

    except Exception as error:
        messagebox.showerror(
            "Concatenation Error",
            f"Could not merge spreadsheets.\n\n{error}",
        )

# ========================================================
# MAIN APPLICATION WINDOW
# ========================================================


def build_concatenator_tab(parent_frame) -> None:

    uploaded_files: list[str] = []

    # Configure root responsive weights
    parent_frame.columnconfigure(0, weight=3)
    parent_frame.columnconfigure(1, weight=2)
    parent_frame.rowconfigure(0, weight=1)

    # ========================================================
    # LEFT PANEL (FILE LIST & CONTROLS)
    # ========================================================

    left_frame = ttk.Frame(
        parent_frame,
        padding=12,
    )
    left_frame.grid(
        row=0,
        column=0,
        sticky="nsew",
    )

    left_frame.rowconfigure(1, weight=1)
    left_frame.columnconfigure(0, weight=1)

    # ----- Section Header -----

    ttk.Label(
        left_frame,
        text="Files to Merge (Drag & Drop here):",
        font=("TkDefaultFont", 10, "bold"),
    ).grid(
        row=0,
        column=0,
        sticky="w",
        pady=(0, 6),
    )

    # ----- Listbox with Scrollbars -----

    list_container = ttk.Frame(left_frame)
    list_container.grid(
        row=1,
        column=0,
        sticky="nsew",
    )

    list_container.rowconfigure(0, weight=1)
    list_container.columnconfigure(0, weight=1)

    file_listbox = tk.Listbox(
        list_container,
        selectmode=tk.EXTENDED,
        font=("TkDefaultFont", 9),
        relief="solid",
        borderwidth=1,
    )
    file_listbox.grid(
        row=0,
        column=0,
        sticky="nsew",
    )

    vertical_scrollbar = ttk.Scrollbar(
        list_container,
        orient="vertical",
        command=file_listbox.yview,
    )
    vertical_scrollbar.grid(
        row=0,
        column=1,
        sticky="ns",
    )

    file_listbox.configure(yscrollcommand=vertical_scrollbar.set)

    # ========================================================
    # FILE MANAGEMENT HELPERS
    # ========================================================

    def add_filepaths(paths: list[str]) -> None:
        valid_extensions = [".csv", ".xlsx", ".xls"]

        for filepath in paths:
            clean_path = str(Path(filepath).resolve())
            extension = Path(clean_path).suffix.lower()

            if (extension in valid_extensions and clean_path not in uploaded_files):
                uploaded_files.append(clean_path)
                file_listbox.insert(
                    tk.END,
                    Path(clean_path).name,
                )

    def select_files() -> None:
        selected = filedialog.askopenfilenames(
            title="Select Spreadsheets",
            filetypes=[
                ("All Spreadsheets", "*.csv *.xlsx *.xls"),
                ("CSV Files", "*.csv"),
                ("Excel Files", "*.xlsx *.xls")
            ],
        )

        if selected:
            add_filepaths(list(selected))

    def remove_selected_files() -> None:
        selected_indexes = list(file_listbox.curselection())

        if not selected_indexes:
            return

        # Delete in reverse order to keep indexes accurate
        for index in reversed(selected_indexes):
            file_listbox.delete(index)
            uploaded_files.pop(index)

    def clear_all_files() -> None:
        file_listbox.delete(0, tk.END)
        uploaded_files.clear()

    # ========================================================
    # DRAG AND DROP SETUP
    # ========================================================

    def on_drop(event) -> None:
        dropped_files = parent_frame.tk.splitlist(event.data)
        add_filepaths(list(dropped_files))

    file_listbox.drop_target_register(DND_FILES)
    file_listbox.dnd_bind("<<Drop>>", on_drop)

    # Bind 'Delete' key on keyboard to delete selected files
    file_listbox.bind("<Delete>", lambda event: remove_selected_files())

    # ----- Left Action Buttons -----

    button_frame = ttk.Frame(left_frame)
    button_frame.grid(
        row=2,
        column=0,
        sticky="ew",
        pady=(10, 0),
    )

    ttk.Button(
        button_frame,
        text="Add Files",
        command=select_files,
    ).pack(
        side="left",
        padx=(0, 5),
    )

    ttk.Button(
        button_frame,
        text="Remove Selected",
        command=remove_selected_files,
    ).pack(
        side="left",
        padx=(0, 5),
    )

    ttk.Button(
        button_frame,
        text="Clear All",
        command=clear_all_files,
    ).pack(side="left")

    # ========================================================
    # RIGHT PANEL (OUTPUT SETTINGS & EXECUTE)
    # ========================================================

    right_frame = ttk.Frame(
        parent_frame,
        padding=12,
    )
    right_frame.grid(
        row=0,
        column=1,
        sticky="nsew",
    )

    right_frame.rowconfigure(4, weight=1)  # Spacer to keep Concat pinned bottom
    right_frame.columnconfigure(0, weight=1)

    # ----- Output File Name -----

    ttk.Label(
        right_frame,
        text="Output File Name:",
        font=("TkDefaultFont", 10, "bold"),
    ).grid(
        row=0,
        column=0,
        sticky="w",
        pady=(0, 4)
    )

    output_entry = ttk.Entry(right_frame)
    output_entry.insert(0, "merged_spreadsheet.csv")
    output_entry.grid(
        row=1,
        column=0,
        sticky="ew",
        pady=(0, 14)
    )

    # ----- Save Destination Folder -----

    ttk.Label(
        right_frame,
        text="Save Location:",
        font=("TkDefaultFont", 10, "bold"),
    ).grid(
        row=2,
        column=0,
        sticky="w",
        pady=(0, 4),
    )

    destination_frame = ttk.Frame(right_frame)
    destination_frame.grid(
        row=3,
        column=0,
        sticky="ew",
    )
    destination_frame.columnconfigure(0, weight=1)

    folder_path_var = tk.StringVar(value=str(Path.cwd()))

    folder_entry = ttk.Entry(
        destination_frame,
        textvariable=folder_path_var,
    )
    folder_entry.grid(
        row=0,
        column=0,
        sticky="ew",
        padx=(0, 6),
    )

    def select_destination_folder() -> None:
        chosen_dir = filedialog.askdirectory(
            title="Select Save Directory",
            initialdir=folder_path_var.get(),
        )

        if chosen_dir:
            folder_path_var.set(chosen_dir)

    ttk.Button(
        destination_frame,
        text="Browse...",
        command=select_destination_folder,
    ).grid(
        row=0,
        column=1,
        sticky="e",
    )

    # ----- Vertical Spacer -----

    ttk.Frame(right_frame).grid(
        row=4,
        column=0,
        sticky="nsew",
    )

    # ----- Concat Action Button -----

    def on_concat_click() -> None:
        concat_files(
            files=uploaded_files,
            output_folder=folder_path_var.get(),
            output_filename=output_entry.get(),
        )

    concat_button = ttk.Button(
        right_frame,
        text="Concatenate File/s",
        command=on_concat_click,
    )
    concat_button.grid(
        row=5,
        column=0,
        sticky="ew",
        ipady=6,
    )