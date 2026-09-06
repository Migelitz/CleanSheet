import os
import sys
import tkinter as tk
from tkinter import ttk

from tkinterdnd2 import TkinterDnD

from about.tab_about import build_about_tab
from cleaner.tab_cleaner import build_cleaner_tab
from concatenator.tab_concat import build_concatenator_tab
from quality.tab_quality import build_quality_checker_tab


def center_window(window: TkinterDnD.Tk, width: int, height: int) -> None:
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    x = (screen_width - width) // 2
    y = (screen_height - height) // 2

    window.geometry(f"{width}x{height}+{x}+{y}")


def main() -> None:

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ASSETS_DIR = os.path.join(BASE_DIR, "assets")

    root = TkinterDnD.Tk()
    root.title("CleanSheet")

    # Cross-platform window icon handling
    ico_path = os.path.join(ASSETS_DIR, "cleansheet_logo.ico")
    png_path = os.path.join(ASSETS_DIR, "cleansheet_logo.png")

    if sys.platform.startswith("win") and os.path.exists(ico_path):
        root.iconbitmap(default=ico_path)
    elif os.path.exists(png_path):
        app_icon = tk.PhotoImage(file=png_path)
        root.iconphoto(True, app_icon)

    # Center window with specific width and height
    center_window(root, width=800, height=480)
    root.minsize(650, 380)

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    concat_tab = ttk.Frame(notebook)
    quality_tab = ttk.Frame(notebook)
    cleaner_tab = ttk.Frame(notebook)
    about_tab = ttk.Frame(notebook)

    notebook.add(concat_tab, text="Spreadsheet Concatenator")
    notebook.add(quality_tab, text="Data Quality Checker")
    notebook.add(cleaner_tab, text="Spreadsheet Cleaner")
    notebook.add(about_tab, text="About")

    build_concatenator_tab(concat_tab)
    build_quality_checker_tab(quality_tab)
    build_cleaner_tab(cleaner_tab)
    build_about_tab(about_tab)

    root.mainloop()


if __name__ == "__main__":
    main()