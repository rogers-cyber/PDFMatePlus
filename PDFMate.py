#!/usr/bin/env python3
"""
PDFMate+ — PDF Combiner & Toolkit (Extended)

Features:
 - Thumbnail preview of PDFs and images
 - Reorder items by dragging inside the list
 - Merge PDFs and images (JPG/PNG → PDF)
 - Optional PDF compression via Ghostscript (gs)
 - Page-level editor: split, rotate, delete pages
 - Thread-safe background processing with progress, log, start/stop
 - Drag & Drop support (requires tkinterdnd2)
 - Light/Dark theme toggle

Dependencies (Python packages):
 pip install PyPDF2 pillow img2pdf tkinterdnd2

System tools required for optional features:
 - Ghostscript (gs must be on system PATH for compression)

Author: Liv Ratha, Phnom Penh, Cambodia
"""

import os
import sys
import time
import threading
import configparser
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path
from io import BytesIO
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinter.simpledialog import askinteger

from PIL import Image, ImageTk

from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from pypdf import PdfReader, PdfWriter

# LICENSE
import hashlib, hmac, queue, atexit
import logging
import pyperclip
import cairosvg
# LICENSE

# Drag & drop
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except Exception:
    HAS_DND = False

# Constants
ASCII_BAR_LEN = 40
THUMB_SIZE = (160, 210)  # px

# File limits
MAX_FILES = 50    # max total files allowed
MAX_SIZE_MB = 25  # max size per file

# ---------------- Constants ----------------
SECRET_SALT = "PPMateRatTool1W6169"
CONFIG_DIR = Path.home() / ".pdfmate"
CONFIG_DIR.mkdir(exist_ok=True)
LICENSE_FILE = CONFIG_DIR / "license.dat"
CONFIG_FILE = CONFIG_DIR / "settings.ini"

logging.basicConfig(level=logging.INFO)

# ---------------- License Helper ----------------
def generate_license_key(email, ltype="personal"):
    """Generate license key based on email + type (deterministic)."""
    return hashlib.sha256(f"{email.lower()}|{ltype}|{SECRET_SALT}".encode()).hexdigest()[:18]

def detect_license_type(email, key):
    """Return the license type from the key (personal/commercial)."""
    for t in ("personal", "commercial"):
        if generate_license_key(email, t) == key:
            return t
    return None

# ---------------- License GUI ----------------
def license_check_dialog(root):
    license_info = {}

    # --- Validate saved license ---
    if LICENSE_FILE.exists():
        try:
            with open(LICENSE_FILE, "r") as f:
                lines = [l.strip() for l in f.read().splitlines() if l.strip()]
            if len(lines) >= 2:
                email, key = lines[0], lines[1]
                ltype = detect_license_type(email, key)
                if ltype:
                    return {"email": email, "key": key, "type": ltype}
        except Exception:
            # fall through to manual activation
            logging.exception("Failed to read existing license file")

    def center_window(win, width=420, height=200):
        win.update_idletasks()
        x = (win.winfo_screenwidth() // 2) - (width // 2)
        y = (win.winfo_screenheight() // 2) - (height // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")

    def validate():
        email = email_var.get().strip().lower()
        key = key_var.get().strip()
        if not email or not key:
            messagebox.showwarning("Invalid Input", "Both Email and License Key are required.")
            return
        ltype = detect_license_type(email, key)
        if ltype:
            try:
                with open(LICENSE_FILE, "w") as f:
                    f.write(f"{email}\n{key}\n")
                try:
                    # tighten permissions on Unix-like systems
                    os.chmod(LICENSE_FILE, 0o600)
                except Exception:
                    pass
            except Exception as e:
                messagebox.showwarning("Warning", f"License saved but failed to set secure permissions: {e}")
            license_info.update({"email": email, "key": key, "type": ltype})
            win.destroy()
        else:
            messagebox.showerror("Invalid License", "License key is invalid!")

    win = tk.Toplevel(root)
    win.title("License Activation")
    center_window(win)
    win.resizable(False, False)

    tk.Label(win, text="Email:").pack(pady=(10, 2))
    email_var = tk.StringVar()
    tk.Entry(win, textvariable=email_var, width=48).pack()

    tk.Label(win, text="License Key:").pack(pady=(8, 2))
    key_var = tk.StringVar()
    tk.Entry(win, textvariable=key_var, width=48).pack()

    tk.Button(win, text="Activate", command=validate, width=12).pack(pady=12)

    win.grab_set()
    root.wait_window(win)
    return license_info or None

# ---------------- Splash Screen Helper -----------------

def resource_path(relative_path):
    """Get path for PyInstaller-extracted files or normal run."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class SplashScreen:
    def __init__(self, root, dark_mode=False, duration=2000):
        self.root = root
        self.dark_mode = dark_mode
        self.duration = duration
        self.progress = 0

        self.splash = tk.Toplevel(root)
        self.splash.overrideredirect(True)
        self.splash.attributes("-topmost", True)

        # Background color depending on theme
        bg_color = "#1e1e2f" if dark_mode else "#ffffff"
        self.splash.configure(bg=bg_color)

        # Splash image or fallback text
        splash_image_path = resource_path("splash.png")
        if os.path.exists(splash_image_path):
            try:
                img = Image.open(splash_image_path)
                self.photo = ImageTk.PhotoImage(img)
                self.label = tk.Label(self.splash, image=self.photo, bg=bg_color)
                self.label.pack(padx=10, pady=10)
            except Exception:
                self.label = tk.Label(self.splash, text="PDFMate+", font=("Segoe UI", 28, "bold"), bg=bg_color,
                                      fg="#ffffff" if dark_mode else "#000000")
                self.label.pack(padx=20, pady=20)
        else:
            self.label = tk.Label(self.splash, text="PDFMate+", font=("Segoe UI", 28, "bold"), bg=bg_color,
                                  fg="#ffffff" if dark_mode else "#000000")
            self.label.pack(padx=20, pady=20)

        # Progress bar
        self.bar_frame = tk.Frame(self.splash, bg=bg_color)
        self.bar_frame.pack(padx=20, pady=(0, 10), fill="x")
        self.bar = tk.Canvas(self.bar_frame, height=10, bg="#555555" if dark_mode else "#cccccc", highlightthickness=0)
        self.bar.pack(fill="x")
        self.fill = self.bar.create_rectangle(0, 0, 0, 10, fill="#4a7abc", width=0)

        # Center splash
        self.splash.update_idletasks()
        w = self.splash.winfo_width()
        h = self.splash.winfo_height()
        ws = self.splash.winfo_screenwidth()
        hs = self.splash.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.splash.geometry(f"{w}x{h}+{x}+{y}")

        # Hide main window while splash is visible
        self.root.withdraw()

        # Animate progress bar
        self.update_progress()

    def update_progress(self):
        self.progress += 2  # increment progress
        if self.progress > 100:
            self.close()
            return
        w = self.bar_frame.winfo_width() * (self.progress / 100)
        self.bar.coords(self.fill, 0, 0, w, 10)
        self.splash.after(int(self.duration / 50), self.update_progress)  # approx 50 steps

    def close(self):
        self.splash.destroy()
        self.root.deiconify()

# ------------------------------
# Load or create settings.ini
# ------------------------------
cfg = configparser.ConfigParser()

if CONFIG_FILE.exists():
    cfg.read(CONFIG_FILE)
else:
    # Default configuration
    cfg["Theme"] = {"dark_mode": "False"}
    cfg["App"] = {"last_output": str(Path.home())}

    # Save to settings.ini in .pdfmate folder
    with open(CONFIG_FILE, "w") as f:
        cfg.write(f)

def seconds_to_hms(s):
    s = int(round(s))
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:02d}"


class PDFMateApp:
    def __init__(self, master):
        self.master = master
        # self.master.title("📚 PDFMate+ — PDF Combiner & Toolkit")
        # self.master.geometry("1100x700")
        # self.master.minsize(900, 560)

        self.master.title("📚 PDFMate+ — PDF Combiner & Toolkit")

        # Get screen resolution
        screen_w = self.master.winfo_screenwidth()
        screen_h = self.master.winfo_screenheight()

        # Window size (70% width, 75% height)
        win_w = int(screen_w * 0.70)
        win_h = int(screen_h * 0.75)

        # Calculate center position
        x = (screen_w // 2) - (win_w // 2)
        y = (screen_h // 2) - (win_h // 2)

        # Apply size & center position
        self.master.geometry(f"{win_w}x{win_h}+{x}+{y}")

        # Minimum window size (optional)
        self.master.minsize(int(screen_w * 0.55), int(screen_h * 0.55))


        # theme
        self.dark_mode = cfg.getboolean("Theme", "dark_mode", fallback=False)
        self._apply_theme()

        # state
        self.items = []  # list of dict {path, type:'pdf'|'img', name}
        self.thumb_cache = {}  # path -> PhotoImage
        self.worker_thread = None
        self.stop_flag = False

        # progress
        self.total_steps = 0
        self.done_steps = 0
        self.start_time = None

        self._lock = threading.Lock()

        # UI
        self._build_ui()
        self._schedule_update()

    # ---------------- theme ----------------
    def _apply_theme(self):
        if self.dark_mode:
            self.bg = "#1e1e2f"
            self.fg = "#ffffff"
            self.btn_bg = "#4a7abc"
            self.panel_bg = "#23232b"
            self.list_bg = "#2b2b2b"
        else:
            self.bg = "#f5f5f5"
            self.fg = "#000000"
            self.btn_bg = "#4a7abc"
            self.panel_bg = "#ffffff"
            self.list_bg = "#ffffff"
        self.master.configure(bg=self.bg)

    def stoggle_theme(self):
        self.dark_mode = not self.dark_mode
        self._apply_theme()
        self._apply_colors_recursive(self.master)

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        cfg["Theme"]["dark_mode"] = str(self.dark_mode)
        with open(CONFIG_FILE, "w") as f:
            cfg.write(f)
        self._apply_theme()
        self._apply_colors_recursive(self.master)

    def show_about(self):
        txt = (
            "📘 PDFMate+ — PDF Combiner & Toolkit\n"
            "---------------------------------------------\n\n"
            "A powerful, all-in-one PDF utility for Windows.\n"
            "This standalone EXE version requires no Python installation.\n\n"

            "🛠 Features:\n"
            "  • Merge PDFs and images (JPG/PNG) into a single PDF\n"
            "  • Drag-and-drop file support and manual file selection\n"
            "  • Reorder items via simple mouse dragging\n"
            "  • Built-in page editor (rotate, delete, split, save)\n"
            "  • Optional PDF compression using Ghostscript\n"
            "  • Multi-threaded processing with progress bar and ETA\n"
            "  • Light/Dark theme toggle\n\n"

            "📁 File Limits (per session):\n"
            f"  • Maximum files: {MAX_FILES}\n"
            f"  • Maximum size per file: {MAX_SIZE_MB} MB\n\n"

            "🔌 External Components (Optional):\n"
            "  • Ghostscript — required only for PDF compression\n\n"

            "💡 System Notes:\n"
            "  • Packaged as a standalone EXE for easy distribution\n"
            "  • Fully portable — no installation required\n\n"

            "🌐 Website: https://matetools.gumroad.com\n"
            "📄 License: Single-User use only. Personal or commercial use permitted. Redistribution prohibited.\n"
            "© 2025 Mate Technologies"
        )
        messagebox.showinfo("About PDFMate+", txt)

    def _apply_colors_recursive(self, widget):
        """
        Apply theme colors to widget and children.
        Handles common Tk widgets plus some ttk styling.
        """
        try:
            # generic containers
            if isinstance(widget, (tk.Frame, tk.LabelFrame, tk.Toplevel)):
                widget.configure(bg=self.panel_bg)
            # labels
            if isinstance(widget, tk.Label):
                widget.configure(bg=self.panel_bg, fg=self.fg)
            # scrolled text / Text
            if isinstance(widget, scrolledtext.ScrolledText) or isinstance(widget, tk.Text):
                widget.configure(bg=self.list_bg, fg=self.fg, insertbackground=self.fg)
            # listbox
            if isinstance(widget, tk.Listbox):
                widget.configure(bg=self.list_bg, fg=self.fg,
                                 selectbackground="#5a5a5a", selectforeground=self.fg)
            # entry
            if isinstance(widget, tk.Entry):
                widget.configure(bg=self.list_bg, fg=self.fg, insertbackground=self.fg)
            # checkbuttons / radiobuttons
            if isinstance(widget, (tk.Checkbutton, tk.Radiobutton)):
                try:
                    widget.configure(bg=self.panel_bg, fg=self.fg, selectcolor=self.btn_bg, activebackground=self.panel_bg)
                except Exception:
                    pass
            # ttk widgets: style update (Progressbar / Scrollbar will use default native style but we can set a simple style)
            try:
                import tkinter.ttk as ttk_mod
                style = ttk_mod.Style()
                # keep style name same across calls
                style.configure("PDFMate.TProgressbar", troughcolor=self.panel_bg, background=self.btn_bg)
                if isinstance(widget, ttk_mod.Progressbar):
                    widget.configure(style="PDFMate.TProgressbar")
            except Exception:
                pass
        except Exception:
            pass

        # recurse
        for c in widget.winfo_children():
            self._apply_colors_recursive(c)

    # ---------------- UI --------------------
    def _build_ui(self):
        top = tk.Frame(self.master, bg=self.bg)
        top.pack(fill="x", padx=10, pady=6)

        tk.Button(top, text="📄 Add Files", bg=self.btn_bg, fg=self.fg, command=self.add_files).pack(side="left", padx=4)
        # tk.Button(top, text="📂 Add Folder", bg=self.btn_bg, fg=self.fg, command=self.add_folder).pack(side="left", padx=4)
        # tk.Button(top, text="🖼 Add Images", bg=self.btn_bg, fg=self.fg, command=self.add_images).pack(side="left", padx=4)
        tk.Button(top, text="🗑 Clear", bg="#d9534f", fg=self.fg, command=self.clear_all).pack(side="left", padx=4)

        tk.Button(top, text="ℹ️ About", bg="#5bc0de", fg=self.fg, command=self.show_about).pack(side="right", padx=4)

        tk.Button(top, text="🌙 Toggle Theme", bg="#777", fg=self.fg, command=self.toggle_theme).pack(side="right", padx=4)

        main = tk.Frame(self.master, bg=self.bg)
        main.pack(fill="both", expand=True, padx=10, pady=6)

        # Left: list + controls
        left = tk.Frame(main, bg=self.panel_bg)
        left.pack(side="left", fill="both", expand=True, padx=6, pady=6)

        tk.Label(left, text="Items to merge (drag to reorder):", bg=self.panel_bg, fg=self.fg, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=6, pady=4)

        lb_frame = tk.Frame(left, bg=self.panel_bg)
        lb_frame.pack(fill="both", expand=True, padx=6, pady=4)

        self.listbox = tk.Listbox(lb_frame, selectmode=tk.SINGLE, bg=self.list_bg, fg=self.fg)
        self.listbox.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(lb_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)

        # Reorder via mouse drag inside listbox
        self.listbox.bind("<Button-1>", self._on_listbox_click)
        self.listbox.bind("<B1-Motion>", self._on_listbox_drag)
        self._drag_index = None

        # DnD to add
        if HAS_DND:
            try:
                self.listbox.drop_target_register(DND_FILES)
                self.listbox.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass

        ctrl = tk.Frame(left, bg=self.panel_bg)
        ctrl.pack(fill="x", padx=6, pady=6)
        tk.Button(ctrl, text="⬆ Move Up", bg="#5bc0de", fg=self.fg, command=self.move_up).pack(side="left", padx=4)
        tk.Button(ctrl, text="⬇ Move Down", bg="#5bc0de", fg=self.fg, command=self.move_down).pack(side="left", padx=4)
        tk.Button(ctrl, text="❌ Remove", bg="#d9534f", fg=self.fg, command=self.remove_selected).pack(side="left", padx=4)
        tk.Button(ctrl, text="✂ Split / Edit Pages", bg="#f0ad4e", fg=self.fg, command=self.open_page_editor).pack(side="left", padx=4)

        # Right: preview + actions
        right = tk.Frame(main, bg=self.panel_bg, width=360)
        right.pack(side="right", fill="y", padx=6, pady=6)

        tk.Label(right, text="Preview", bg=self.panel_bg, fg=self.fg, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=6, pady=4)

        # preview metadata
        self.meta_label = tk.Label(right, text="", justify="left", bg=self.panel_bg, fg=self.fg, anchor="w")
        self.meta_label.pack(fill="x", padx=6)

        # OCR / options
        label_opt = tk.Label(right, text="Options", bg=self.panel_bg, fg=self.fg)
        opt = tk.LabelFrame(right, labelwidget=label_opt, bg=self.panel_bg)


        opt.pack(fill="x", padx=6, pady=6)

        self.compress_var = tk.BooleanVar(value=False)

        self.compress_btn = tk.Checkbutton(
            opt,
            text="Compress output (Ghostscript)",
            variable=self.compress_var,
            bg=self.panel_bg,
            fg=self.fg,
            selectcolor="#4a7abc",
            anchor="w"
        )
        
        self.compress_btn.pack(anchor="w", padx=6, pady=2)

        # output & start/stop
        out_frame = tk.Frame(right, bg=self.panel_bg)
        out_frame.pack(fill="x", padx=6, pady=6)
        tk.Label(out_frame, text="Output filename:", bg=self.panel_bg, fg=self.fg).pack(anchor="w")
        self.output_entry = tk.Entry(out_frame)
        self.output_entry.pack(fill="x", pady=3)

        btns = tk.Frame(right, bg=self.panel_bg)
        btns.pack(fill="x", padx=6, pady=6)
        self.start_btn = tk.Button(btns, text="🚀 Merge/Process", bg="#4a7abc", fg=self.fg, command=self.start_processing)
        self.start_btn.pack(side="left", fill="x", expand=True, padx=4)
        self.stop_btn = tk.Button(btns, text="🛑 Stop", bg="#777", fg=self.fg, state="disabled", command=self.request_stop)
        self.stop_btn.pack(side="left", fill="x", expand=True, padx=4)

        # progress & log (bottom)

        label_prog = tk.Label(self.master, text="Progress & Log", bg=self.panel_bg, fg=self.fg)
        prog_frame = tk.LabelFrame(self.master, labelwidget=label_prog, bg=self.panel_bg)

        prog_frame.pack(fill="both", expand=True, padx=10, pady=6)

        self.ascii_label = tk.Label(prog_frame, text="[" + " " * ASCII_BAR_LEN + "]", font=("Consolas", 10), bg=self.panel_bg, fg=self.fg)
        self.ascii_label.pack(anchor="w", padx=6, pady=3)

        stat = tk.Frame(prog_frame, bg=self.panel_bg)
        stat.pack(fill="x", padx=6)
        self.percent_label = tk.Label(stat, text="0.0%", bg=self.panel_bg, fg=self.fg)
        self.percent_label.pack(side="left")
        self.eta_label = tk.Label(stat, text="ETA: --:--:--", bg=self.panel_bg, fg=self.fg)
        self.eta_label.pack(side="right")
        self.count_label = tk.Label(prog_frame, text="Processed: 0/0", bg=self.panel_bg, fg=self.fg)
        self.count_label.pack(anchor="w", padx=6)

        self.ttk_prog = ttk.Progressbar(prog_frame, orient="horizontal", mode="determinate")
        self.ttk_prog.pack(fill="x", padx=6, pady=6)

        self.log_box = scrolledtext.ScrolledText(prog_frame, height=8, bg=self.list_bg, fg=self.fg)
        self.log_box.pack(fill="both", expand=True, padx=6, pady=4)

        # bind selection change
        self.listbox.bind("<<ListboxSelect>>", lambda e: self.on_select())

        # apply colors
        self._apply_colors_recursive(self.master)

    # ------------- UI helper & logging -------------
    def _safe_log(self, msg):
        if threading.current_thread() is threading.main_thread():
            self._append_log(msg)
        else:
            self.master.after(0, lambda: self._append_log(msg))

    def _append_log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert(tk.END, f"[{ts}] {msg}\n")
        self.log_box.see(tk.END)

    # ------------------ Aggregated Add Items ------------------
    def _add_items(self, paths):
        """Add multiple files with limit checks, show aggregated warnings."""
        skipped = []

        for path in paths:
            path = os.path.abspath(path)
            if not os.path.exists(path):
                skipped.append(f"{path} (missing)")
                continue

            # Stop if max file count reached
            if len(self.items) >= MAX_FILES:
                skipped.append(f"{os.path.basename(path)} (max files reached)")
                continue

            # Stop if file too large
            try:
                size_mb = os.path.getsize(path) / (1024 * 1024)
                if size_mb > MAX_SIZE_MB:
                    skipped.append(f"{os.path.basename(path)} ({size_mb:.1f} MB > {MAX_SIZE_MB} MB)")
                    continue
            except Exception:
                skipped.append(f"{os.path.basename(path)} (size check failed)")
                continue

            ext = os.path.splitext(path)[1].lower()
            typ = "pdf" if ext == ".pdf" else "img"

            # Reject duplicates
            if any(it["path"] == path for it in self.items):
                continue

            # Add item
            name = os.path.basename(path)
            self.items.append({"path": path, "type": typ, "name": name})
            self.listbox.insert(tk.END, name)
            self._safe_log(f"Added: {path}")

        # Show aggregated warning if some files were skipped
        if skipped:
            messagebox.showwarning(
                "Skipped Files",
                "Some files were not added:\n" + "\n".join(skipped)
            )


    # ------------------ Updated File Selection Methods ------------------
    def add_files(self):
        files = filedialog.askopenfilenames(
            title="Select PDF & image files",
            filetypes=[("PDF & images", "*.pdf;*.png;*.jpg;*.jpeg;*.tif;*.tiff")]
        )
        if files:
            self._add_items(files)

    def add_images(self):
        files = filedialog.askopenfilenames(
            title="Select image files",
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.tif;*.tiff")]
        )
        if files:
            self._add_items(files)

    def add_folder(self):
        folder = filedialog.askdirectory(title="Select folder")
        if not folder:
            return

        files_to_add = []
        for root_dir, _, files in os.walk(folder):
            for fn in files:
                if fn.lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff")):
                    files_to_add.append(os.path.join(root_dir, fn))

        if files_to_add:
            self._add_items(files_to_add)

    def _on_drop(self, event):
        files = self.master.tk.splitlist(event.data)
        if files:
            self._add_items(files)

    def clear_all(self):
        self.items.clear()
        self.listbox.delete(0, tk.END)

        # Clear preview safely
        if hasattr(self, "thumb_label"):
            self.thumb_label.config(image="", text="No selection")

        if hasattr(self, "meta_label"):
            self.meta_label.config(text="")

        if hasattr(self, "thumb_cache"):
            self.thumb_cache.clear()

        self._safe_log("Cleared items.")

    def remove_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        i = sel[0]
        removed = self.items.pop(i)
        self.listbox.delete(i)
        self._safe_log(f"Removed {removed['name']}")

        # Safely clear preview widgets
        if hasattr(self, "thumb_label"):
            self.thumb_label.config(image="", text="No selection")

        if hasattr(self, "meta_label"):
            self.meta_label.config(text="")

    def move_up(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        self.items[i-1], self.items[i] = self.items[i], self.items[i-1]
        text = self.listbox.get(i)
        self.listbox.delete(i)
        self.listbox.insert(i-1, text)
        self.listbox.selection_set(i-1)

    def move_down(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] >= len(self.items) - 1:
            return
        i = sel[0]
        self.items[i+1], self.items[i] = self.items[i], self.items[i+1]
        text = self.listbox.get(i)
        self.listbox.delete(i)
        self.listbox.insert(i+1, text)
        self.listbox.selection_set(i+1)

    # ------------ listbox drag reorder handlers -----------
    def _on_listbox_click(self, event):
        # remember index under mouse
        try:
            self._drag_index = self.listbox.nearest(event.y)
        except Exception:
            self._drag_index = None

    def _on_listbox_drag(self, event):
        idx = self.listbox.nearest(event.y)
        if self._drag_index is None or idx == self._drag_index:
            return
        # swap in UI and data
        try:
            a = self._drag_index
            b = idx
            # swap listbox entries and items
            a_text = self.listbox.get(a)
            b_text = self.listbox.get(b)
            self.listbox.delete(a)
            self.listbox.insert(a, b_text)
            self.listbox.delete(b)
            self.listbox.insert(b, a_text)
            self.items[a], self.items[b] = self.items[b], self.items[a]
            self._drag_index = b
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(b)
        except Exception:
            pass

    # -------------- preview ----------------
    def on_select(self):
        sel = self.listbox.curselection()
        if not sel:
            self.meta_label.config(text="No selection")
            return

        i = sel[0]
        item = self.items[i]
        path = item["path"]

        # Show only file info
        meta = f"File: {item['name']}\nType: {item['type'].upper()}\nPath: {path}"
        self.meta_label.config(text=meta)

    # ---------------- processing (merge/OCR/compress) --------------

    def start_processing(self):
        """Start merging/processing items (PDFs or images) in a background thread."""
        if not self.items:
            messagebox.showwarning("No items", "Please add PDF(s) or image(s) first.")
            return

        # Get output path
        out = self.output_entry.get().strip()
        if not out:
            out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
            if not out:
                return
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, out)
        self.output_path = os.path.abspath(out)

        # Prepare progress tracking
        with self._lock:
            self.total_steps = len(self.items)
            self.done_steps = 0
            self.start_time = time.time()
            self.stop_flag = False

        # Disable/enable buttons
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        # Start worker thread
        self.worker_thread = threading.Thread(target=self._worker_merge, daemon=True)
        self.worker_thread.start()
        self._safe_log(f"Started processing -> {self.output_path}")


    def request_stop(self):
        """Request to stop the background processing."""
        if hasattr(self, "worker_thread") and self.worker_thread.is_alive():
            self.stop_flag = True
            self._safe_log("Stop requested...")


    def _worker_merge(self):
        """Worker thread: merge PDFs/images, optional compression, save final PDF."""
        tmpdir = tempfile.mkdtemp(prefix="pdfmate_")
        final_out = None
        writer = PdfWriter()
        step = 0

        try:
            for item in list(self.items):
                if self.stop_flag:
                    self._safe_log("Processing stopped by user.")
                    return

                path = item["path"]
                typ = item["type"]

                if not os.path.exists(path):
                    self._safe_log(f"Skipping missing file: {path}")
                    with self._lock:
                        self.done_steps += 1
                    continue

                self._safe_log(f"Processing {os.path.basename(path)}")

                try:
                    if typ == "pdf":
                        reader = PdfReader(path)
                        for page in reader.pages:
                            writer.add_page(page)
                    else:
                        # Convert image -> PDF
                        img = Image.open(path).convert("RGB")
                        img.info['dpi'] = (100, 100)
                        tmp_pdf = os.path.join(tmpdir, f"img_{step}.pdf")
                        img.save(tmp_pdf, "PDF")
                        reader = PdfReader(tmp_pdf)
                        for page in reader.pages:
                            writer.add_page(page)

                except Exception as e:
                    self._safe_log(f"Failed to process {path}: {e}")

                with self._lock:
                    self.done_steps += 1
                step += 1

            # Write merged PDF
            if writer.pages:
                temp_out = os.path.join(tmpdir, "out_raw.pdf")
                try:
                    with open(temp_out, "wb") as f:
                        writer.write(f)
                    final_out = temp_out
                    self._safe_log(f"Merged written (raw) -> {temp_out}")
                except Exception as e:
                    self._safe_log(f"Failed to write merged PDF: {e}")
                    return
            else:
                self._safe_log("No valid files to merge; exiting worker.")
                return

            # Optional compression
            if getattr(self, "compress_var", None) and self.compress_var.get() and final_out and os.path.exists(final_out):
                compressed = os.path.join(tmpdir, "out_compressed.pdf")
                ok = self._compress_pdf_with_ghostscript(final_out, compressed)
                if ok and os.path.exists(compressed):
                    final_out = compressed
                    self._safe_log("Compression complete.")
                else:
                    self._safe_log("Compression failed; using uncompressed PDF.")

            # Move final PDF to output path
            if final_out and os.path.exists(final_out):
                os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
                os.replace(final_out, self.output_path)
                self._safe_log(f"Final saved -> {self.output_path}")
            else:
                self._safe_log("No final PDF to save; process may have failed.")

        except Exception as e:
            self._safe_log(f"Worker error: {e}")

        finally:
            # Cleanup temp dir
            try:
                for f in os.listdir(tmpdir):
                    try:
                        os.remove(os.path.join(tmpdir, f))
                    except Exception:
                        pass
                os.rmdir(tmpdir)
            except Exception:
                pass

            # Re-enable buttons in UI thread
            if hasattr(self, "master"):
                self.master.after(0, lambda: self.start_btn.config(state="normal"))
                self.master.after(0, lambda: self.stop_btn.config(state="disabled"))
            self._safe_log("Processing finished.")


    def _compress_pdf_with_ghostscript(self, input_pdf, output_pdf, quality="ebook"):
        """
        Compress a PDF using Ghostscript.
        'quality' may be: screen, ebook, printer, prepress, default
        Returns True on success, False on failure.
        """
        gs = shutil.which("gs")
        if not gs:
            self._safe_log("Ghostscript not found; skipping compression.")
            return False

        q_map = {
            "screen": "/screen",
            "ebook": "/ebook",
            "printer": "/printer",
            "prepress": "/prepress",
            "default": "/default"
        }
        q = q_map.get(quality, "/ebook")

        cmd = [
            gs, "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS={q}",
            "-dNOPAUSE", "-dQUIET", "-dBATCH",
            f"-sOutputFile={output_pdf}", input_pdf
        ]

        try:
            subprocess.run(cmd, check=True)
            return True
        except Exception as e:
            self._safe_log(f"Ghostscript compress failed: {e}")
            return False

    # ----------------- page editor (split/rotate/delete) -----------------

    def open_page_editor(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("Select PDF", "Select a PDF item to edit pages.")
            return

        idx = sel[0]
        item = self.items[idx]

        if item["type"] != "pdf":
            messagebox.showinfo("PDF required", "Page editing requires a PDF file.")
            return

        if not os.path.exists(item["path"]):
            messagebox.showerror("File Not Found", f"The file does not exist:\n{item['path']}")
            return

        try:
            PageEditor(
                self.master,
                item["path"],
                on_save_callback=lambda new_path: self._replace_item_path(idx, new_path)
            )
        except Exception as e:
            messagebox.showerror("Failed to open PDF", f"Cannot open this PDF:\n{str(e)}")

        # try:
        #     PageEditor(
        #         self.master,
        #         item["path"],
        #         on_save_callback=lambda new_path: self._replace_item_path(idx, new_path)
        #     )
        # except Exception as e:
        #     messagebox.showerror("PDF Error", f"Failed to open PDF: File use very old format!!!")

    def _replace_item_path(self, index, new_path):
        # replace item in list and update UI
        self.items[index]["path"] = new_path
        self.items[index]["name"] = os.path.basename(new_path)
        self.listbox.delete(index)
        self.listbox.insert(index, self.items[index]["name"])
        self._safe_log(f"Replaced item with edited file: {new_path}")

    # ---------------- update UI progress ----------------
    def _schedule_update(self):
        self._update_ui()
        self.master.after(300, self._schedule_update)

    def _update_ui(self):
        with self._lock:
            total = self.total_steps if self.total_steps else max(1, len(self.items))
            done = self.done_steps
            start = self.start_time

        pct = min(100.0, (done / total) * 100.0) if total else 0.0
        filled = int((pct / 100.0) * ASCII_BAR_LEN)
        bar = "[" + ("#" * filled).ljust(ASCII_BAR_LEN) + "]"
        self.ascii_label.config(text=bar)
        self.percent_label.config(text=f"{pct:5.1f}%")
        try:
            self.ttk_prog["value"] = pct
        except Exception:
            pass
        self.count_label.config(text=f"Processed: {done}/{total}")

        if start and done > 0 and total > 0:
            elapsed = time.time() - start
            rate = done / elapsed if elapsed > 0 else 0.0
            remain = max(0, total - done)
            eta = remain / rate if rate > 0 else 0
            self.eta_label.config(text=f"ETA: {seconds_to_hms(eta)}")
        else:
            self.eta_label.config(text="ETA: --:--:--")


# ---------------- Page Editor UI Class -----------------

class PageEditor:
    def __init__(self, master, pdf_path, on_save_callback=None):
        self.master = tk.Toplevel(master)
        self.master.title("Page Editor - " + os.path.basename(pdf_path))
        self.master.geometry("520x360")
        self.pdf_path = pdf_path
        self.on_save_callback = on_save_callback
        self.master.grab_set()

        # Check if file exists
        if not os.path.exists(pdf_path):
            messagebox.showerror("File Not Found", f"The file does not exist:\n{pdf_path}")
            self.master.destroy()
            return

        # Load PDF safely
        try:
            self.reader = PdfReader(pdf_path)
        except Exception as e:
            messagebox.showerror("Failed to open PDF", f"Cannot open this PDF:\n{str(e)}")
            self.master.destroy()
            return

        self.pages = list(range(len(self.reader.pages)))  # current ordering
        self.selected = set()

        self._build_ui()

    def _build_ui(self):
        top = tk.Frame(self.master)
        top.pack(fill="both", expand=True, padx=6, pady=6)

        # Left: listbox + controls
        left = tk.Frame(top)
        left.pack(side="left", fill="both", expand=True)

        tk.Label(left, text=f"Pages in {os.path.basename(self.pdf_path)}").pack(anchor="w")
        self.lb = tk.Listbox(left, selectmode=tk.EXTENDED)
        self.lb.pack(fill="both", expand=True)
        for i in range(len(self.pages)):
            self.lb.insert(tk.END, f"Page {i+1}")

        ctrl = tk.Frame(left)
        ctrl.pack(fill="x", pady=6)
        tk.Button(ctrl, text="Rotate +90", command=lambda: self.rotate_selected(90)).pack(side="left", padx=4)
        tk.Button(ctrl, text="Rotate -90", command=lambda: self.rotate_selected(-90)).pack(side="left", padx=4)
        tk.Button(ctrl, text="Delete Selected", command=self.delete_selected).pack(side="left", padx=4)
        tk.Button(ctrl, text="Split Out Selected", command=self.split_selected).pack(side="left", padx=4)

        # Right: actions
        right = tk.Frame(top, width=240)
        right.pack(side="right", fill="y", padx=6)

        tk.Button(right, text="Save As...", bg="#4a7abc", fg="white", command=self.save_as).pack(fill="x", pady=6)
        tk.Button(right, text="Cancel", command=self.master.destroy).pack(fill="x", pady=6)

    def rotate_selected(self, deg):
        sel = list(self.lb.curselection())
        if not sel:
            return

        for idx in sel:
            page = self.reader.pages[idx]
            try:
                page.rotate(deg)  # pypdf rotate
            except Exception as e:
                messagebox.showerror("Rotation Error", f"Failed to rotate page {idx+1}:\n{str(e)}")

        messagebox.showinfo("Rotated", "Rotations applied in-memory. Use Save As to persist.")

    def delete_selected(self):
        sel = list(self.lb.curselection())
        if not sel:
            return

        writer = PdfWriter()
        for i in range(len(self.reader.pages)):
            if i not in sel:
                writer.add_page(self.reader.pages[i])

        # Use temporary file to reload reader
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.close()
        try:
            with open(tmp.name, "wb") as f:
                writer.write(f)
            self.reader = PdfReader(tmp.name)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete pages:\n{str(e)}")
            return

        for i in sorted(sel, reverse=True):
            self.lb.delete(i)

        messagebox.showinfo("Deleted", "Selected pages removed in-memory. Use Save As to persist.")

    def split_selected(self):
        sel = list(self.lb.curselection())
        if not sel:
            return

        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if not out:
            return

        writer = PdfWriter()
        for i in sel:
            writer.add_page(self.reader.pages[i])

        try:
            with open(out, "wb") as f:
                writer.write(f)
            messagebox.showinfo("Split", f"Saved selected pages to {out}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to split pages:\n{str(e)}")

    def save_as(self):
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if not out:
            return

        writer = PdfWriter()
        for p in self.reader.pages:
            writer.add_page(p)

        try:
            with open(out, "wb") as f:
                writer.write(f)
            messagebox.showinfo("Saved", f"Saved edited PDF to {out}")
            if self.on_save_callback:
                try:
                    self.on_save_callback(out)
                except Exception:
                    pass
            self.master.destroy()
        except Exception as e:
            messagebox.showerror("Save Failed", f"Failed to save PDF:\n{str(e)}")

# ------------------ Utilities ---------------------
def shutil_which(name):
    """Cross-platform which (pure python fallback)"""
    from shutil import which
    exe = which(name) or which("gswin64c") or which("gswin32c")
    return exe

# ------------------ Main -------------------------
def main():
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()


    root.withdraw()  # Hide main window

    license_info = license_check_dialog(root)
    if not license_info:
        messagebox.showwarning("License Required", "A valid license is required.")
        root.destroy()
        sys.exit(1)

    dark_mode = cfg.getboolean("Theme", "dark_mode", fallback=False)

    # Show splash screen with animated progress
    SplashScreen(root, dark_mode=dark_mode, duration=2000)
    app = PDFMateApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: root.destroy())
    root.mainloop()


if __name__ == "__main__":
    main()
