import logging
import os
import platform
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk
from typing import Any, cast
from urllib.parse import quote

from cleansheet.updater.update_checker import (
    UpdateInfo,
    check_for_update,
    get_current_version,
)

logger = logging.getLogger(__name__)

from PIL import Image, ImageTk

from cleansheet.paths import ASSETS_DIR

# CONFIGURATION 

__version__ = get_current_version()
update_check_running = False

def open_link(url: str) -> bool:
    """Open a URL in the user's default web browser."""
    try:
        opened = webbrowser.open_new_tab(url)
    except Exception:
        logger.exception("Could not open external link")
        messagebox.showerror(
            "Unable to Open Link",
            "CleanSheet could not open the link in your default browser.",
        )
        return False

    if not opened:
        logger.warning("Default browser declined to open external link")
        messagebox.showerror(
            "Unable to Open Link",
            "CleanSheet could not open the link in your default browser.",
        )
        return False

    logger.debug("Opened external link")
    return True

def open_feedback_email() -> None:
    """Open the feedback client and provide a manual fallback."""
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
        f"App: CleanSheet Utility {__version__}\n"
        f"OS: {user_os} {os_release}"
    )

    # Safely convert spaces and symbols so web browsers can read them
    mailto_url = f"mailto:{email}?subject={quote(subject)}&body={quote(body)}"

    try:
        opened = webbrowser.open(mailto_url, new=2)
    except Exception:
        logger.exception("Could not open feedback email client")
        messagebox.showerror(
            "Unable to Open Email",
            "CleanSheet could not open your email client. You can use the manual copy option instead.",
        )
    else:
        if not opened:
            logger.warning("Default email client declined to open mailto link")
            messagebox.showerror(
                "Unable to Open Email",
                "CleanSheet could not open your email client. You can use the manual copy option instead.",
            )
        else:
            logger.info("Feedback email workflow opened")

    # ============================================================================
    # Manual copy-paste option for users who may have issues with the mailto link
    # ============================================================================

    try:
        dialog = tk.Toplevel()
        dialog.title("Send Feedback")
        dialog.geometry("520x420")
        dialog.resizable(False, False)
        dialog.focus_set()
        dialog.lift()
    except Exception:
        logger.exception("Could not create feedback fallback dialog")
        messagebox.showerror(
            "Unable to Send Feedback",
            "CleanSheet could not open the manual feedback window.",
        )
        return
    
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
        try:
            dialog.clipboard_clear()
            dialog.clipboard_append(text)
            dialog.update()
        except Exception:
            logger.exception("Could not copy feedback text to clipboard")
            messagebox.showerror(
                "Unable to Copy",
                "CleanSheet could not copy the text to your clipboard.",
                parent=dialog,
            )
            return

        logger.debug("Copied feedback text to clipboard")
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
    try:
        img = Image.open(os.path.join(ASSETS_DIR, "icons", "cleansheet_logo.png"))
        img = img.resize((150, 150))
        logo_img = ImageTk.PhotoImage(img)
        
        logo_label = ttk.Label(main_container, image=logo_img)
        cast(Any, logo_label).image = logo_img
        logo_label.pack(pady=(0, 10))

    except Exception:
        logger.warning("Could not load application logo", exc_info=True)

    # ----- Title & Version -----
    title_label = ttk.Label(
        main_container,
        text="CleanSheet",
        font=("TkDefaultFont", 24, "bold")
    )
    title_label.pack(pady=(10, 2))

    version_label = ttk.Label(
        main_container,
        text=__version__,
        font=("TkDefaultFont", 10)
    )
    version_label.pack(pady=(0, 5))

    # ----- Update checking -----
    def popup_update_window(result: UpdateInfo) -> None:
        update_window = tk.Toplevel()
        update_window.title("Update Available")
        update_window.resizable(False, False)

        # Keep the popup above the main application.
        update_window.transient(parent_frame.winfo_toplevel())

        update_container = ttk.Frame(
            update_window,
            padding=24,
        )
        update_container.pack(fill="both", expand=True)

        # ----- Header -----
        header_label = ttk.Label(
            update_container,
            text="Update Available",
            font=("TkDefaultFont", 16, "bold"),
        )
        header_label.pack(pady=(0, 6))

        description_label = ttk.Label(
            update_container,
            text="A newer version of CleanSheet is available.",
            font=("TkDefaultFont", 10),
        )
        description_label.pack(pady=(0, 18))

        # ----- Version Information -----
        version_frame = ttk.Frame(update_container)
        version_frame.pack(fill="x", pady=(0, 20))

        ttk.Label(
            version_frame,
            text="Current version:",
            font=("TkDefaultFont", 10),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 20),
            pady=3,
        )

        ttk.Label(
            version_frame,
            text=result.current_version,
            font=("TkDefaultFont", 10, "bold"),
        ).grid(
            row=0,
            column=1,
            sticky="e",
            pady=3,
        )

        ttk.Label(
            version_frame,
            text="Latest version:",
            font=("TkDefaultFont", 10),
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 20),
            pady=3,
        )

        ttk.Label(
            version_frame,
            text=result.latest_version,
            font=("TkDefaultFont", 10, "bold"),
        ).grid(
            row=1,
            column=1,
            sticky="e",
            pady=3,
        )

        version_frame.columnconfigure(1, weight=1)

        # ----- Buttons -----
        button_container = ttk.Frame(update_container)
        button_container.pack()

        view_button = ttk.Button(
            button_container,
            text="View Update",
            command=lambda: open_link(result.release_url),
        )
        view_button.pack(
            side="left",
            padx=5,
        )

        later_button = ttk.Button(
            button_container,
            text="Later",
            command=update_window.destroy,
        )
        later_button.pack(
            side="left",
            padx=5,
        )

        # ----- Window Positioning -----
        update_window.update_idletasks()

        parent_window = parent_frame.winfo_toplevel()

        parent_x = parent_window.winfo_x()
        parent_y = parent_window.winfo_y()
        parent_width = parent_window.winfo_width()
        parent_height = parent_window.winfo_height()

        popup_width = update_window.winfo_width()
        popup_height = update_window.winfo_height()

        x = parent_x + (parent_width - popup_width) // 2
        y = parent_y + (parent_height - popup_height) // 2

        update_window.geometry(f"+{x}+{y}")

        update_window.grab_set()
        update_window.focus_set()

    def handle_update_result(result: UpdateInfo | None) -> None:
        if result is None:
            logger.debug("Update check returned no result; restoring update button")
            update_button.config(
                text="Check for Updates",
                state="normal",
            )
            return

        if result.update_available:
            logger.info(
                "Update available: current=%s latest=%s",
                result.current_version,
                result.latest_version,
            )
            update_button.config(
                text="Update Available",
                state="normal",
            )

            try:
                popup_update_window(result)
            except Exception:
                logger.exception("Could not display update-available window")
                update_button.config(
                    text="Check for Updates",
                    state="normal",
                )
                messagebox.showerror(
                    "Unable to Show Update",
                    "CleanSheet found an update but could not display the update window.",
                    parent=parent_frame.winfo_toplevel(),
                )

        else:
            logger.info("No CleanSheet update is available")
            update_button.config(
                text="Up to Date",
                state="normal",
            )

            # Little delay to show 'Up to date' text
            parent_frame.after(2500, lambda: update_button.config(text="Check for Updates"))

    def handle_update_failure() -> None:
        """Restore the update control and report an unexpected worker failure."""
        update_button.config(
            text="Check for Updates",
            state="normal",
        )
        messagebox.showerror(
            "Unable to Check for Updates",
            "CleanSheet could not complete the update check. Please try again later.",
            parent=parent_frame.winfo_toplevel(),
        )

    def check_update() -> None:
        """Run the update check in the background."""

        global update_check_running

        if update_check_running:
            logger.warning("Check update is already running. Dropping new run.")
            return

        update_check_running = True
        logger.debug("Starting background update check")

        try:
            result = check_for_update()

        except Exception:
            logger.exception("Unexpected failure during update check")

            try:
                parent_frame.after(0, handle_update_failure)

            except Exception:
                logger.exception("Could not schedule update failure callback")

        else:
            try:
                parent_frame.after(0, lambda: handle_update_result(result))

            except Exception:
                logger.exception("Could not schedule update result callback")

        finally:
            update_check_running = False

    def check_update_on_startup() -> None:
        """Run a silent update check during application startup."""
        logger.debug("Starting automatic startup update check")

        try:
            result = check_for_update()
        except Exception:
            logger.exception("Unexpected failure during startup update check")
            return

        if result is None:
            logger.debug("Startup update check returned no result")
            return

        if not result.update_available:
            logger.debug("No update available during startup check")
            return

        logger.info(
            "Startup update check found a new version: current=%s latest=%s",
            result.current_version,
            result.latest_version,
        )

        parent_frame.after(0, lambda: popup_update_window(result))

    def start_startup_update_check() -> None:
        """Start the automatic update check without blocking the GUI."""
        threading.Thread(
            target=check_update_on_startup,
            daemon=True,
        ).start()

    def start_check_update() -> None:
        """Start the update check without blocking the GUI."""

        logger.info("User initiated update check")

        update_button.config(
            text="Checking...",
            state="disabled",
        )

        # To keep GUI responsive while checking update
        try:
            threading.Thread(
                target=check_update,
                daemon=True,
            ).start()
        except Exception:
            logger.exception("Could not start update-check worker")
            update_button.config(
                text="Check for Updates",
                state="normal",
            )
            messagebox.showerror(
                "Unable to Check for Updates",
                "CleanSheet could not start the update check. Please try again.",
                parent=parent_frame.winfo_toplevel(),
            )

    update_button = ttk.Button(
        main_container,
        text="Check for Updates",
        cursor="hand2",
        command=start_check_update,
    )
    update_button.pack(pady=(5, 10))

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

    parent_frame.after(1000, start_startup_update_check)