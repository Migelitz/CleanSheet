import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import pandas as pd
from tkinterdnd2 import DND_FILES

# ========================================================
# DATA PROCESSING FUNCTIONS
# ========================================================

def stream_to_csv(
    files: list[str],
    output_path: Path,
    chunksize: int = 50_000
) -> None:
    
    """Streams CSV and Excel files into a single CSV file in chunks to minimize RAM."""
    is_first_write = True

    for filepath in files:
        extension = Path(filepath).suffix.lower()

        if extension == ".csv":
            # Stream CSV in chunks to avoid loading full dataset into memory
            for chunk in pd.read_csv(filepath, chunksize=chunksize):

                chunk.to_csv(
                    output_path,
                    mode="w" if is_first_write else "a",
                    header=is_first_write,
                    index=False
                )
                is_first_write = False

        elif extension in [".xlsx", ".xls"]:
            # Load individual excel file, write immediately, then free memory
            df = pd.read_excel(filepath, engine="calamine")

            df.to_csv(
                output_path,
                mode="w" if is_first_write else "a",
                header=is_first_write,
                index=False
            )
            is_first_write = False

        else:
            raise ValueError(f"Unsupported format: {extension}")


def concat_files(
    files: list[str],
    output_folder: str,
    output_filename: str,
    chunksize: int = 50_000
) -> None:
    
    """Merges all files directly to disk and saves them to the specified directory."""

    folder_path = Path(output_folder.strip())

    if not folder_path.exists() or not folder_path.is_dir():
        raise ValueError("The selected destination folder does not exist.")

    clean_filename = output_filename.strip()

    if not clean_filename:
        clean_filename = "merged_spreadsheet.csv"

    output_path = folder_path / clean_filename
    extension = output_path.suffix.lower()

    try:
        # Default destination format to CSV if extension is unspecified or non-excel
        # Protect the program from crashing from the user who enters output name with other file extension like .txt
        if extension not in [".xlsx", ".xls"]:
            if extension != ".csv":
                output_path = output_path.with_suffix(".csv")

            stream_to_csv(files=files, output_path=output_path, chunksize=chunksize)
            
        else:
            # Excel export: Stream to temporary CSV first, then convert one-by-one
            # to prevent keeping all DataFrames in memory simultaneously
            temp_csv = folder_path / f"~temp_{clean_filename}.csv"
            stream_to_csv(files=files, output_path=temp_csv, chunksize=chunksize)

            with pd.ExcelWriter(
                output_path,
                engine="xlsxwriter",
                engine_kwargs={'options': {'constant_memory': True}}
                ) as writer:

                current_row = 0

                for chunk in pd.read_csv(temp_csv, chunksize=chunksize):

                    if current_row + len(chunk) > 1_048_576:
                        messagebox.showwarning(
                            "Excel Row Limit",
                            "Merged data exceeds Excel's row limit of 1,048,576 rows. "
                            "Only the first 1,048,576 rows will be saved to the Excel file. "
                            "Please consider exporting to CSV for larger datasets.",
                        )

                        remaining_rows = 1_048_576 - current_row
                        if remaining_rows > 0:
                            chunk.iloc[:remaining_rows].to_excel(   # [:remaining_rows] is panda slicing to limit the number of rows written to Excel
                                writer,
                                index=False,
                                startrow=current_row,
                                header=current_row == 0 # If start of file, write header; otherwise, skip header
                            )

                        # If the row limit is reached, break out of the loop to stop writing more data
                        break

                    chunk.to_excel(
                        writer,
                        index=False,
                        startrow=current_row,
                        header=current_row == 0
                    )
                    current_row += len(chunk)

            # Delete temp_csv file after using
            if temp_csv.exists():
                temp_csv.unlink()

            messagebox.showinfo(
                "Success",
                f"Successfully merged {len(files)} files into:\n\n{output_folder}",
            )
    except Exception as e:
        messagebox.showerror(
            "Error",
            f"An error occurred while merging files:\n\n{str(e)}"
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
    horizontal_scrollbar = ttk.Scrollbar(
        list_container,
        orient="horizontal",
        command=file_listbox.xview
    )

    vertical_scrollbar.grid(
        row=0,
        column=1,
        sticky="ns",
    )
    horizontal_scrollbar.grid(
        row=1,
        column=0,
        sticky="ew"
    )


    file_listbox.configure(
        yscrollcommand=vertical_scrollbar.set,
        xscrollcommand=horizontal_scrollbar.set
    )

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
            elif extension not in valid_extensions:
                messagebox.showwarning(
                    "Unsupported File Type",
                    f"The file '{Path(clean_path).name}' has an unsupported format.\n\n"
                    "Supported formats are: CSV (.csv), Excel (.xlsx, .xls)."
                )
            elif clean_path in uploaded_files:
                messagebox.showinfo(
                    "Duplicate File",
                    f"The file '{Path(clean_path).name}' has already been added."
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
            messagebox.showinfo(
                "No Selection",
                "Please select at least one file to remove from the list."
            )
            return

        # Delete in reverse order to keep indexes accurate
        # Why? Because if you delete from the start, the indexes of the remaining items shift, leading to potential errors or skipped deletions. Deleting from the end ensures that the indexes of the items you want to delete remain valid as you remove them.
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
        cursor="hand2",
        command=select_files
    ).pack(
        side="left",
        padx=(0, 5),
    )

    ttk.Button(
        button_frame,
        text="Remove Selected",
        cursor="hand2",
        command=remove_selected_files
    ).pack(
        side="left",
        padx=(0, 5),
    )

    ttk.Button(
        button_frame,
        text="Clear All",
        cursor="hand2",
        command=clear_all_files
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

    right_frame.rowconfigure(6, weight=1)  # Spacer to keep Concat pinned bottom
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

    folder_path_entry = ttk.Entry(destination_frame)
    folder_path_entry.insert(0, str(Path.cwd()))
    folder_path_entry.grid(
        row=0,
        column=0,
        sticky="ew",
        padx=(0, 6),
    )

    def select_destination_folder() -> None:
        chosen_dir = filedialog.askdirectory(
            title="Select Save Directory",
            initialdir=folder_path_entry.get(),
        )

        if chosen_dir:
            folder_path_entry.delete(0, tk.END)
            folder_path_entry.insert(0, str(Path(chosen_dir).resolve()))

    ttk.Button(
        destination_frame,
        text="Browse...",
        cursor="hand2",
        command=select_destination_folder
    ).grid(
        row=0,
        column=1,
        sticky="e",
    )

    # ----- Chunk Size Entry -----

    chunk_size_label = ttk.Label(
        right_frame,
        text="Chunk Size (rows):",
        font=("TkDefaultFont", 10, "bold"),
    )
    chunk_size_label.grid(
        row=4,
        column=0,
        sticky="w",
        pady=(0, 4)
    )

    tooltip_button = ttk.Button(
        right_frame,
        text="ⓘ",
        style="Toolbutton",
        cursor="hand2",
        command=lambda: messagebox.showinfo(
            "Chunk Size Information",
            "The chunk size determines how many rows are processed at a time during the merge.\n\n"
            "Larger chunk sizes may speed up processing but use more memory.\n"
            "Smaller chunk sizes reduce memory usage but may take longer to complete.\n\n"
            "Default chunk size is 50,000 rows. You can adjust this value based on your system's memory capacity and the size of the files being merged."
        )
    )
    tooltip_button.grid(
        row=4,
        column=0,
        sticky="e",
        pady=(0, 4)
    )

    chunk_size_frame = ttk.Frame(right_frame)
    chunk_size_frame.grid(
        row=5,
        column=0,
        sticky="ew"
    )
    chunk_size_frame.columnconfigure(0, weight=1)

    chunk_size_entry = ttk.Entry(chunk_size_frame)
    chunk_size_entry.insert(0, "50000")
    chunk_size_entry.grid(
        row=0,
        column=0,
        sticky="ew",
        padx=(0, 6)
    )

    ttk.Button(
        chunk_size_frame,
        cursor="hand2",
        text="Set Chunk Size",
        command=lambda: messagebox.showinfo(
            "Chunk Size Set",
            f"Chunk size set to {chunk_size_entry.get()} rows."
        )
    ).grid(
        row=0,
        column=1,
        sticky="e",
    )

    chunk_size_entry.bind(
        "<Return>",
        lambda event: messagebox.showinfo(
            "Chunk Size Set",
            f"Chunk size set to {chunk_size_entry.get()} rows."
        )
    )

    # ----- Vertical Spacer -----

    ttk.Frame(right_frame).grid(
        row=6,
        column=0,
        sticky="nsew",
    )

    # ----- Concat Action Button -----

    def on_concat_click() -> None:

        if not uploaded_files:
            messagebox.showwarning(
                "No Files Selected", "Please select at least one file to merge."
            )
            return

        concat_button.config(state=tk.DISABLED, text="Merging...")

        # Progress window to indicate that the merging process is ongoing
        progress_win = tk.Toplevel(parent_frame)
        progress_win.title("Progress...")

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
            text="Merging files...\nPlease wait.",
            justify="center"
        ).pack(pady=15)
        
        progress = ttk.Progressbar(progress_win, mode="indeterminate")
        progress.pack(fill="x", padx=20)
        progress.start()

        def merge_in_thread():
            try:
                concat_files(
                    files=uploaded_files,
                    output_folder=folder_path_entry.get(),
                    output_filename=output_entry.get(),
                    chunksize=int(chunk_size_entry.get())
                )

                parent_frame.after(0, on_success)

            except Exception as e:
                parent_frame.after(0, lambda error=str(e): on_error(error))

        def on_success():
            progress.stop()
            progress_win.grab_release() # Return control to the main window
            progress_win.destroy()
            concat_button.config(state=tk.NORMAL, text="Concatenate Files")

        def on_error(error: str):
            progress.stop()
            progress_win.grab_release() # Return control to the main window
            progress_win.destroy()
            concat_button.config(state=tk.NORMAL, text="Concatenate Files")

        # Start the merging process in a separate thread to keep the GUI responsive
        threading.Thread(target=merge_in_thread, daemon=True).start()

    concat_button = ttk.Button(
        right_frame,
        text="Concatenate Files",
        cursor="hand2",
        command=on_concat_click
    )
    concat_button.grid(
        row=7,
        column=0,
        sticky="ew",
        ipady=6,
    )