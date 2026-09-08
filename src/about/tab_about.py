import os
import platform
import tkinter as tk
import webbrowser
from tkinter import ttk
from urllib.parse import quote

from PIL import Image, ImageTk

# CONFIGURATION 

version = "1.0.0"

def open_link(url: str) -> None:
    """Opens a URL in the user's default web browser."""
    webbrowser.open_new_tab(url)

def open_feedback_email() -> None:
    email = "macalla.chyrusmiguel@gmail.com"
    subject = "Support & Feedback - CleanSheet Utility"
    user_os = platform.system()
    os_release = platform.release()

    # Pre-formatting a helpful body template for the user
    body = (
        "Please describe your feedback, suggestions, features, bugs, or ideas here:\n"
        "(Your feedback here)\n\n"

        "---------------------------\n"
        "Technical Details (Do not change):\n"
        f"App: CleanSheet Utility {version}\n"
        f"OS: {user_os} {os_release}"
    )

    # Safely convert spaces and symbols so web browsers can read them
    mailto_url = f"mailto:{email}?subject={quote(subject)}&body={quote(body)}"

    webbrowser.open(mailto_url, new=2)  # This triggers the OS to open their default mail client

    # ============================================================================
    # Manual copy-paste option for users who may have issues with the mailto link
    # ============================================================================

    dialog = tk.Toplevel()
    dialog.title("Send Feedback")
    dialog.geometry("520x420")
    dialog.resizable(False, False)
    dialog.focus_set()
    dialog.lift()
    
    # Container with padding
    container = ttk.Frame(dialog, padding="16")
    container.pack(fill="both", expand=True)

    header = ttk.Label(
        container,
        text="Didn't open in your email client?",
        font=("TkDefaultFont", 11, "bold")
    )
    header.pack(anchor="w")

    subheader = ttk.Label(
        container,
        text="You can send your feedback manually using the details below:",
        font=("TkDefaultFont", 9),
        foreground="#555555"
    )
    subheader.pack(anchor="w", pady=(2, 12))

    # Helper for temporary button feedback
    def copy_with_feedback(button: ttk.Button, text: str, default_label: str) -> None:
        dialog.clipboard_clear()
        dialog.clipboard_append(text)
        dialog.update()
        button.config(text="Copied!")
        dialog.after(1500, lambda: button.config(text=default_label))

    # Recipient Field
    email_frame = ttk.Frame(container)
    email_frame.pack(fill="x", pady=(0, 10))

    ttk.Label(email_frame, text="To:", width=6).pack(side="left")
    email_entry = ttk.Entry(email_frame)
    email_entry.insert(0, email)
    email_entry.config(state="readonly")
    email_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

    copy_email_btn = ttk.Button(email_frame, text="Copy Email", width=12)
    copy_email_btn.config(command=lambda: copy_with_feedback(copy_email_btn, email, "Copy Email"))
    copy_email_btn.pack(side="right")

    # Template Body Preview
    ttk.Label(container, text="Message Template:").pack(anchor="w", pady=(0, 4))
    
    text_box = tk.Text(
        container, 
        height=8, 
        wrap="word", 
        font=("TkDefaultFont", 9),
        relief="solid", 
        borderwidth=1
    )
    text_box.insert("1.0", body)
    text_box.config(state="disabled")
    text_box.pack(fill="both", expand=True, pady=(0, 12))

    # Footer Actions
    btn_bar = ttk.Frame(container)
    btn_bar.pack(fill="x", side="bottom", pady=(12, 0))

    copy_body_btn = ttk.Button(btn_bar, text="Copy Template")
    copy_body_btn.config(command=lambda: copy_with_feedback(copy_body_btn, body, "Copy Template"))
    copy_body_btn.pack(side="left")

    close_btn = ttk.Button(btn_bar, text="Done", command=dialog.destroy)
    close_btn.pack(side="right")

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
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ASSETS_DIR = os.path.abspath(os.path.join(BASE_DIR, "../", "assets", "icons"))

    try:
        img = Image.open(os.path.join(ASSETS_DIR, "cleansheet_logo.png"))
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
    def seperator(frame: ttk.Frame) -> None:
        sep = ttk.Label(
            links_frame,
            text="•",
            foreground="#0066cc",
            font=("TkDefaultFont", 11)
        )
        sep.pack(padx=8, pady=4, side="left")

    links_frame = ttk.Frame(main_container)
    links_frame.pack(pady=10)

    # 1. Project Repository Link
    repo_link = ttk.Label(
        links_frame,
        text="View Project on GitHub",
        foreground="#0066cc", # Hyperlink blue
        font=("TkDefaultFont", 11, "underline"),
        cursor="hand2" # Changes mouse to a pointer hand on hover
    )
    repo_link.pack(pady=4, side="left")
    repo_link.bind(
        "<Button-1>", 
        lambda e: open_link("https://github.com/Migelitz/CleanSheet")
    )

    seperator(links_frame)

    # 2. Author Profile Link
    profile_link = ttk.Label(
        links_frame,
        text="Visit Author's GitHub Profile",
        foreground="#0066cc",
        font=("TkDefaultFont", 11, "underline"),
        cursor="hand2"
    )
    profile_link.pack(pady=4, side="left")
    profile_link.bind(
        "<Button-1>", 
        lambda e: open_link("https://github.com/Migelitz")
    )

    seperator(links_frame)

    # 3. User Feedback Link
    feedback_link = ttk.Label(
        links_frame,
        text="Send Feedback",
        foreground="#0066cc",
        font=("TkDefaultFont", 11, "underline"),
        cursor="hand2"
    )
    feedback_link.pack(pady=4, side="left")
    feedback_link.bind(
        "<Button-1>",
        lambda e: open_feedback_email(), 
    )
