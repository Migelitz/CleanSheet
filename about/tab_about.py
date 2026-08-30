import webbrowser
import tkinter as tk

from tkinter import ttk
from PIL import Image, ImageTk

# CONFIGURATION 

version = "1.0.0"

def open_link(url: str) -> None:
    """Opens a URL in the user's default web browser."""
    webbrowser.open_new_tab(url)

def build_about_tab(parent_frame: ttk.Frame) -> None:

    parent_frame.columnconfigure(0, weight=1)
    parent_frame.rowconfigure(0, weight=1)

    # Allow scroll feature
    canvas = tk.Canvas(
        parent_frame,
        highlightthickness=0
    )

    canvas.grid(
        row=0,
        column=0,
        sticky="nsew"
    )

    # ----- Scrollbar -----
    scrollbar = ttk.Scrollbar(
        parent_frame,
        orient="vertical",
        command=canvas.yview
    )

    scrollbar.grid(
        row=0,
        column=1,
        sticky="ns"
    )

    canvas.configure(yscrollcommand=scrollbar.set)

    # ----- Scrollable Container -----
    main_container = ttk.Frame(canvas, padding=20)

    container_window = canvas.create_window(
        (0,0),
        window=main_container,
        anchor="nw"

    )

    # Make container follow Canvas width
    def resize_container(event):
        canvas.itemconfigure(
            container_window,
            width=event.width
        )

    canvas.bind("<Configure>", resize_container)

    # Update scrollable area whenever main_container changes size
    main_container.bind(
        "<Configure>",
        lambda event: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    # ----- Mouse Wheel Scrolling -----
    # Handles different mousewheel keybinds for windows and linux
    def on_mousewheel(event):
        if event.num == 4:          # Linux scroll up
            canvas.yview_scroll(-1, "units")
        elif event.num == 5:        # Linux scroll down
            canvas.yview_scroll(1, "units")
        elif event.delta:           # Windows
            canvas.yview_scroll(
                int(-event.delta / 120),
                "units"
            )

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


    # ----- Logo Icon -----
    try:
        img = Image.open("assets/cleansheet_logo.png")
        img = img.resize((150, 150))
        logo_img = ImageTk.PhotoImage(img)
        
        logo_label = ttk.Label(main_container, image=logo_img)
        logo_label.image = logo_img 
        logo_label.pack(pady=(0, 10))

    except Exception as e:
        print(f"Could not load logo: {e}")

    # ----- Title & Version -----
    title_label = ttk.Label(
        main_container,
        text="CleanSheet",
        font=("TkDefaultFont", 24, "bold")
    )
    title_label.pack(pady=(10, 2))

    version_label = ttk.Label(
        main_container,
        text=f"Version {version}",
        font=("TkDefaultFont", 10)
    )
    version_label.pack(pady=(0, 20))


    # ----- Description -----
    description_text = (
        "CleanSheet is a lightweight desktop utility designed to automate\n"
        "day-to-day data preparation tasks. It provides a seamless interface\n"
        "to merge, profile, and clean spreadsheets without writing code."
    )
    
    desc_label = ttk.Label(
        main_container,
        text=description_text,
        wraplength=700,
        justify="center",
        font=("TkDefaultFont", 11)
    )
    desc_label.pack(pady=(0, 30))

    # ----- Author Information -----
    author_label = ttk.Label(
        main_container,
        text="Authored by: Chyrus Miguel D. Macalla",
        font=("TkDefaultFont", 12, "bold")
    )
    author_label.pack(pady=(0, 10))

    # ----- Clickable Links -----
    links_frame = ttk.Frame(main_container)
    links_frame.pack(pady=10)

    # 1. Project Repository Link
    repo_link = ttk.Label(
        links_frame,
        text="🔗 View Project on GitHub",
        foreground="#0066cc", # Hyperlink blue
        font=("TkDefaultFont", 11, "underline"),
        cursor="hand2" # Changes mouse to a pointer hand on hover
    )
    repo_link.pack(pady=4)
    repo_link.bind(
        "<Button-1>", 
        lambda e: open_link("https://github.com/Migelitz/CleanSheet")
    )

    # 2. Author Profile Link
    profile_link = ttk.Label(
        links_frame,
        text="👤 Visit Author's GitHub Profile",
        foreground="#0066cc",
        font=("TkDefaultFont", 11, "underline"),
        cursor="hand2"
    )
    profile_link.pack(pady=4)
    profile_link.bind(
        "<Button-1>", 
        lambda e: open_link("https://github.com/Migelitz")
    )