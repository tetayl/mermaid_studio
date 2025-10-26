#!/usr/bin/env python3
import os
import sys
import uuid
import shutil
import subprocess
import threading
import tempfile
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from datetime import datetime
from code_editor import MermaidEditor
from preview_pane import PreviewPane
from example_data import list_examples, get_example
import re
import json
import webbrowser
from theme import ThemeManager

APP_VERSION = "0.2.4"

APP_TITLE = "Mermaid Studio - Python UI"
DEFAULT_SAMPLE = """flowchart TD
    A[Friday afternoon] --> B{Do you feel lucky?}
    B -->|Yes| C[Deploy! 🚀]
    B -->|No| D[Go home 🏠]
    C --> E{Production on fire? 🔥}
    E -->|Yes| F[Panic & rollback!]
    E -->|No| G[Celebrate 🎉]
    F --> G
"""

class MermaidStudio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry("1200x700")
        self.minsize(800, 500)

        # Theme manager
        self.theme_manager = ThemeManager(self)

        # Chrome path
        self.chrome_path: str | None = self._find_chrome()


        # State
        self.current_file: Path | None = None
        self.last_png: Path | None = None
        self.mmdc_path: str | None = self._find_mmdc()
        self.render_lock = threading.Lock()
        self.dirty = False
        self.protocol("WM_DELETE_WINDOW", self._on_exit)

                
        # Recent files state
        self.recent_files = []
        self.recent_files_path = Path.home() / ".config" / "mermaid_studio" / "recent.json"
        self._load_recent_files()

        # Auto render state
        self.auto_render_var = tk.BooleanVar(value=False)
        self.auto_render_job = None          # handle from after()
        self.pending_autorender = False      # true if edits happened during an active render
        self.last_rendered_hash = None       # hash of last rendered code
        self._code_hash_being_rendered = None

        self._build_ui()
        self._new_document(initial_text=DEFAULT_SAMPLE)
        self.iconphoto(False, tk.PhotoImage(file="assets/appicon.png"))
        messagebox.showinfo(APP_TITLE, f"Mermaid Studio v{APP_VERSION}\n \nSimple Python UI wrapper for mermaid-cli.")


    # - UI building
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # File Menu
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", command=self._new_document, accelerator="Ctrl+N")
        file_menu.add_command(label="Open...", command=self._open_file, accelerator="Ctrl+O")
        file_menu.add_separator()

        # --- Open Recent submenu ---
        self.recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade( label="Recent", menu=self.recent_menu)

        file_menu.add_separator()
        file_menu.add_command(label="Save", command=self._save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self._save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Export PNG As...", command=self._export_png_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_exit)
        menubar.add_cascade(label="File", menu=file_menu)

        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command( label="Undo", accelerator="Ctrl+Z", command=lambda: self._editor_event("<<Undo>>"))
        edit_menu.add_command( label="Redo", accelerator="Ctrl+Y", command=lambda: self._editor_event("<<Redo>>"))
        edit_menu.add_separator()
        edit_menu.add_command( label="Cut", accelerator="Ctrl+X", command=lambda: self._editor_event("<<Cut>>"))
        edit_menu.add_command(label="Copy", accelerator="Ctrl+C", command=lambda: self._editor_event("<<Copy>>"))
        edit_menu.add_command( label="Paste", accelerator="Ctrl+V", command=lambda: self._editor_event("<<Paste>>"))
        edit_menu.add_separator()
        edit_menu.add_command( label="Select All", accelerator="Ctrl+A", command=lambda: self._editor_select_all())
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # Example menu
        examples_menu = tk.Menu(menubar, tearoff=0)
        for name in sorted(list_examples()):
            examples_menu.add_command(
                label=name,
                command=lambda n=name: self._apply_example(n)
            )
        menubar.add_cascade(label="Examples", menu=examples_menu)

        # Settings menu
        self.settings_menu = tk.Menu(menubar, tearoff=0)
        self.settings_menu.add_command(label="Set mmdc path...", command=self._set_mmdc_path)

        # Mermaid diagram theme submenu
        self.diagram_theme_var = tk.StringVar(value=self.theme_manager.get_diagram_theme())
        self.diagram_theme_menu = tk.Menu(self.settings_menu, tearoff=0)
        for label, value in [
            ("Default", "default"),
            ("Forest", "forest"),
            ("Dark", "dark"),
            ("Neutral", "neutral"),
        ]:
            self.diagram_theme_menu.add_radiobutton(
                label=label,
                value=value,
                variable=self.diagram_theme_var,
                command=lambda v=value: self._on_diagram_theme_selected(v),
            )
        self.settings_menu.add_cascade(label="Mermaid diagram theme", menu=self.diagram_theme_menu)


        # Sketch mode toggle
        self.sketch_var = tk.BooleanVar(value=self.theme_manager.get_sketch_mode())
        self.settings_menu.add_checkbutton(
            label="Sketch style (hand-drawn)",
            variable=self.sketch_var,
            command=self._on_sketch_toggled,
        )

        # UI Theme toggle (light/dark)
        self.settings_menu.add_command(label="Use Dark Theme", command=self._toggle_theme_clicked)

        self.settings_menu.add_separator()
        self.settings_menu.add_command(label="About", command=self._about)
        menubar.add_cascade(label="Settings", menu=self.settings_menu)


        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(
            label="Keyboard Shortcuts…",
            command=self._show_shortcuts_dialog
        )
        help_menu.add_separator()
        help_menu.add_command(
            label="Mermaid Docs…",
            command=self._open_mermaid_docs
        )
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

        self.config(menu=menubar)

        # Toolbar
        self.toolbar = ttk.Frame(self, padding=(6, 4))
        self.toolbar.grid(row=0, column=0, sticky="ew")   # grid is fine here (toolbar in root)

        # Left-aligned controls
        self.render_btn = ttk.Button(self.toolbar, text="Render", command=self._render_clicked)
        self.render_btn.pack(side="left", padx=(0, 8))

        self.auto_cb = ttk.Checkbutton(
            self.toolbar, text="Auto render", variable=self.auto_render_var,
            command=self._on_autorender_toggle
        )
        self.auto_cb.pack(side="left")

        # Right-aligned status
        self.status = ttk.Label(self.toolbar, text="Ready", anchor="e")
        self.status.pack(side="right")

        # Paned window: editor | preview
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.grid(row=1, column=0, sticky="nsew")

        # Editor (Mermaid-aware)
        editor_frame = ttk.Frame(paned)
        editor_frame.rowconfigure(0, weight=1)   # editor row grows
        editor_frame.rowconfigure(1, weight=0)   # log row, fixed height
        editor_frame.columnconfigure(0, weight=1)

        self.editor = MermaidEditor(editor_frame)
        self.editor.grid(row=0, column=0, sticky="nsew")

        # Error log (hidden by default)
        self.err_frame = ttk.Frame(editor_frame)
        self.err_text = tk.Text(
            self.err_frame,
            height=6,
            wrap="word",
            state="disabled",
            background="#fff8f8",
            foreground="#7a0000",
            font=("Courier New", 11),
        )
        self.err_scroll = ttk.Scrollbar(self.err_frame, orient="vertical", command=self.err_text.yview)
        self.err_text.configure(yscrollcommand=self.err_scroll.set)
        self.err_text.grid(row=0, column=0, sticky="nsew")
        self.err_scroll.grid(row=0, column=1, sticky="ns")
        self.err_frame.rowconfigure(0, weight=1)
        self.err_frame.columnconfigure(0, weight=1)

        # Start hidden
        self.err_frame.grid(row=1, column=0, sticky="nsew")
        self.err_frame.grid_remove()

        # Change callback
        self.editor.on_change(self._on_editor_changed)

        paned.add(editor_frame, weight=1)

        # Preview
        preview_frame = ttk.Frame(paned)
        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)


        from preview_pane import PreviewPane
        self.preview = PreviewPane(preview_frame, bg="#f5f5f5")
        self.preview.grid(row=0, column=0, sticky="nsew")


        paned.add(preview_frame, weight=1)
        # Set divider to 50% once the window has been drawn
        self.after(100, lambda: paned.sashpos(0, self.winfo_width() // 3))

        # Key bindings
        self.bind_all("<Control-n>", lambda e: self._new_document())
        self.bind_all("<Control-o>", lambda e: self._open_file())
        self.bind_all("<Control-s>", lambda e: self._save_file())
        self._rebuild_recent_menu()

        # Give ThemeManager references so it can repaint
        self.theme_manager.toolbar = self.toolbar
        self.theme_manager.status_label = self.status
        self.theme_manager.editor_widget = self.editor
        self.theme_manager.err_text = self.err_text
        self.theme_manager.err_frame = self.err_frame
        self.theme_manager.preview_widget = self.preview

        # Apply whichever theme was loaded (light or dark)
        self.theme_manager.apply_theme()

        # Make sure the toggle menu item shows the alternative theme
        self._update_theme_menu_label()

    
    def _rebuild_recent_menu(self):
        """Refresh the Open Recent submenu."""
        # Clear it first
        self.recent_menu.delete(0, "end")

        if not self.recent_files:
            # gray disabled item if no recent files
            self.recent_menu.add_command(
                label="(No recent files)",
                state="disabled"
            )
        else:
            # Add each path
            for idx, fpath in enumerate(self.recent_files, start=1):
                nice_label = Path(fpath).name
                full_path = fpath  # capture now for lambda default
                self.recent_menu.add_command(
                    label=f"{idx}. {nice_label}",
                    command=lambda p=full_path: self._open_recent_file(p)
                )
            self.recent_menu.add_separator()
            self.recent_menu.add_command(
                label="Clear list",
                command=self._clear_recent_files
            )

    def _on_diagram_theme_selected(self, theme_name: str):
        # Tell ThemeManager
        self.theme_manager.set_diagram_theme(theme_name)
        # Status bar feedback (optional)
        self._set_status(f"Diagram theme: {theme_name}")


    def _toggle_theme_clicked(self):
        # flip theme
        self.theme_manager.toggle_theme()
        # update menu label every time
        self._update_theme_menu_label()

    def _update_theme_menu_label(self):
        # In self.settings_menu:
        # index 0 = "Set mmdc path..."
        # index 1 = theme toggle item
        # index 2 = separator
        # index 3 = "About"

        if self.theme_manager.current_name == "dark":
            new_label = "Use Light Theme"
        else:
            new_label = "Use Dark Theme"

        self.settings_menu.entryconfig(3, label=new_label)

    def _on_sketch_toggled(self):
        enabled = bool(self.sketch_var.get())
        self.theme_manager.set_sketch_mode(enabled)
        # tiny UX touch
        self._set_status("Sketch style: on" if enabled else "Sketch style: off")



    def _errorlog_show(self, text: str, status_msg: str | None = None):
        # Trim puppeteer stack noise if present (Parser3.parseError and below)
        cutoff = text.find("Parser3.parseError")
        if cutoff != -1:
            text = text[:cutoff].rstrip()

        cleaned = text.strip()

        self.err_text.configure(state="normal")
        self.err_text.delete("1.0", "end")
        self.err_text.insert("1.0", cleaned + "\n")
        self.err_text.configure(state="disabled")
        self.err_frame.grid()  # make sure it's visible

        if status_msg is None:
            status_msg = "Render failed - see error log"
        self._set_status(status_msg)

    def _errorlog_hide(self):
        # Clear and hide
        self.err_text.configure(state="normal")
        self.err_text.delete("1.0", "end")
        self.err_text.configure(state="disabled")
        self.err_frame.grid_remove()

    def _editor_event(self, sequence: str):
        # Safely forward to the underlying Text widget inside MermaidEditor
        try:
            self.editor.text.event_generate(sequence)
        except Exception:
            pass

    def _editor_select_all(self):
        try:
            self.editor.text.tag_add("sel", "1.0", "end-1c")
            self.editor.text.see("insert")
            self.editor.text.focus_set()
        except Exception:
            pass


    def _on_editor_changed(self):
        self.dirty = True
        self._set_status("Edited")
        if self.auto_render_var.get():
            self._schedule_autorender()

    def _on_autorender_toggle(self):
        if self.auto_render_var.get():
            self._schedule_autorender()
        else:
            self._cancel_autorender()
            self._set_status("Auto render off")

    def _schedule_autorender(self, delay_ms: int = 5000):
        # reset any existing timer
        if self.auto_render_job is not None:
            try:
                self.after_cancel(self.auto_render_job)
            except Exception:
                pass
            self.auto_render_job = None
        # schedule a new one
        self.auto_render_job = self.after(delay_ms, self._auto_render_fire)
        self._set_status(f"Auto render in {delay_ms // 1000} s")

    def _cancel_autorender(self):
        if self.auto_render_job is not None:
            try:
                self.after_cancel(self.auto_render_job)
            except Exception:
                pass
            self.auto_render_job = None

    def _auto_render_fire(self):
        self.auto_render_job = None
        code = self.editor.get()
        code = code if code is not None else ""
        code_hash = hash(code)
        if not code.strip():
            self._set_status("Nothing to render")
            return
        if self.last_rendered_hash is not None and code_hash == self.last_rendered_hash:
            self._set_status("No changes since last render")
            return
        if self.render_lock.locked():
            # a render is in progress, queue another once it finishes
            self.pending_autorender = True
            self._set_status("Render in progress - will auto render next")
            return
        # trigger a render now
        self._render_clicked()


    def _about(self):
        messagebox.showinfo(APP_TITLE, "Simple Python UI wrapper for mermaid-cli (mmdc).\n \n"
                                       "Edit Mermaid code, then Render to preview and export PNG.")

    # - File operations
    def _new_document(self, initial_text: str = ""):
        if not self._maybe_prompt_save():
            return
        self.current_file = None
        self._set_title()
        self.editor.set_text((initial_text.strip() + "\n \n") if initial_text else "")
        self.status.configure(text="New document")
        self.editor.focus_editor()

    def _open_file(self):
        if not self._maybe_prompt_save():
            return
        path = filedialog.askopenfilename(
            title="Open Mermaid file",
            filetypes=[("Mermaid files", "*.mmd *.mermaid *.mmdc"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.editor.set_text(content)
            self.current_file = Path(path)
            self._set_title()
            self._set_status(f"Opened {Path(path).name}")
            self.editor.focus_editor()

            self._add_recent_file(self.current_file)

        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{e}")

    def _maybe_prompt_save(self) -> bool:
        """Ask to save unsaved changes. Return True if it's OK to proceed."""
        if not self.dirty:
            return True

        response = messagebox.askyesnocancel(
            "Unsaved changes",
            "You have unsaved changes. Do you want to save them before continuing?",
        )
        if response is None:
            # Cancel pressed
            return False
        if response:
            saved = self._save_file()
            if saved is None:
                return False
        # Either saved or chose "No"
        return True

    def _save_file(self, force_dialog: bool = False):
        if self.current_file is None or force_dialog:
            return self._save_file_as()
        try:
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(self.editor.get())
            self.status.configure(text=f"Saved {self.current_file.name}")
            self.dirty = False
            return self.current_file
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file:\n{e}")

    def _save_file_as(self):
        path = filedialog.asksaveasfilename(
            title="Save Mermaid file",
            defaultextension=".mmd",
            filetypes=[("Mermaid file", "*.mmd"), ("All files", "*.*")],
        )
        if not path:
            return
        self.current_file = Path(path)
        self._set_title()

        self._add_recent_file(self.current_file)

        return self._save_file()

    def _on_exit(self):
        if self._maybe_prompt_save():
            self.destroy()

    def _export_png_as(self):
        if self.last_png is None or not self.last_png.exists():
            messagebox.showwarning("No preview yet", "Please render first to generate a preview.")
            return
        dest = filedialog.asksaveasfilename(
            title="Export PNG As",
            defaultextension=".png",
            initialfile=(self.current_file.stem + ".png") if self.current_file else "diagram.png",
            filetypes=[("PNG Image", "*.png")],
        )
        if not dest:
            return
        try:
            shutil.copy(self.last_png, dest)
            self.status.configure(text=f"Exported PNG to {Path(dest).name}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not export PNG:\n{e}")

    def _apply_example(self, name: str):
        """Load an example diagram into the editor."""
        try:
            code = get_example(name)
        except KeyError:
            messagebox.showerror("Error", f"Example '{name}' not found.")
            return
        self.editor.set_text(code)
        self.current_file = None
        self._set_title()
        self._set_status(f"Loaded example: {name}")

    def _load_recent_files(self):
        """Load recent files list from disk."""
        try:
            data_dir = self.recent_files_path.parent
            data_dir.mkdir(parents=True, exist_ok=True)

            if self.recent_files_path.exists():
                with open(self.recent_files_path, "r", encoding="utf-8") as f:
                    arr = json.load(f)
                # keep only files that still exist
                self.recent_files = [p for p in arr if Path(p).exists()]
            else:
                self.recent_files = []
        except Exception:
            self.recent_files = []

    def _save_recent_files(self):
        """Persist recent files to disk."""
        try:
            with open(self.recent_files_path, "w", encoding="utf-8") as f:
                json.dump(self.recent_files, f, indent=2)
        except Exception:
            pass  # don't crash UI if writing fails

    def _add_recent_file(self, path: Path):
        """Add a file path to the MRU list and rebuild the menu."""
        p = str(path)
        # move to front, dedupe
        self.recent_files = [f for f in self.recent_files if f != p]
        self.recent_files.insert(0, p)
        # cap at 5
        self.recent_files = self.recent_files[:5]
        self._save_recent_files()
        self._rebuild_recent_menu()

    def _clear_recent_files(self):
        """Clear MRU list."""
        self.recent_files = []
        self._save_recent_files()
        self._rebuild_recent_menu()

    def _open_recent_file(self, filepath: str):
        """Open file from recent list without showing the file picker."""
        path = Path(filepath)
        if not path.exists():
            # file missing → remove from list and warn
            messagebox.showwarning("File not found", f"{path} no longer exists.")
            self.recent_files = [f for f in self.recent_files if f != filepath]
            self._save_recent_files()
            self._rebuild_recent_menu()
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.editor.set_text(content)
            self.current_file = path
            self._set_title()
            self._set_status(f"Opened {path.name}")
            self.editor.focus_editor()
            # bump it to front again
            self._add_recent_file(path)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{e}")



    # - Render
    def _render_clicked(self):
        # stop any pending auto render to avoid double work
        self._cancel_autorender()

        if not self.mmdc_path:
            if not self._prompt_set_mmdc_path():
                return

        code = self.editor.get()
        if code is None:
            code = ""
        self._code_hash_being_rendered = hash(code)

        # Warn early if this diagram type is likely unsupported/experimental
        self._maybe_warn_diagram_type(code)

        # Prepare code_to_render with optional sketch header
        sketch_enabled = self.theme_manager.get_sketch_mode()
        diagram_theme = self.theme_manager.get_diagram_theme()

        # Do we already have some kind of config/init block at the top?
        # We'll skip injecting if the user already has frontmatter (starts with '---')
        # OR an init directive (%%{init: ...}%%). We don't want to double-config.
        has_frontmatter = code.lstrip().startswith("---")
        has_init_block = code.lstrip().startswith("%%{init:")

        if sketch_enabled and not (has_frontmatter or has_init_block):
            # Build an init header that sets theme + handDrawn true
            # We include the diagram theme here as well, so CLI and header agree.
            header = (
                "---\n"
                "config:\n"
                f"  look: handDrawn\n"
                f"  theme: {diagram_theme}\n"
                "---\n"
            )
            code_to_render = header + code
        else:
            code_to_render = code

        # Write under $HOME/mermaid_studio_cache so the Snap can read it
        cache_dir = Path.home() / ".cache" / "mermaid_studio"
        cache_dir.mkdir(parents=True, exist_ok=True)

        import uuid
        temp_input_path = cache_dir / f"mstudio_{uuid.uuid4().hex}.mmd"
        with open(temp_input_path, "w", encoding="utf-8") as f:
            f.write(code_to_render)
        # Ensure readable by confined processes
        os.chmod(temp_input_path, 0o644)

        # If a document is saved, render PNG next to it. Otherwise, use cache path
        if self.current_file:
            out_dir = self.current_file.parent
            out_png = out_dir / (self.current_file.stem + ".png")
        else:
            #out_png = cache_dir / f"mstudio_{uuid.uuid4().hex}.png"
            out_png = cache_dir / f"mstudio_preview.png"

        self._render_async(input_file=temp_input_path, output_png=out_png)

    def _show_shortcuts_dialog(self):
        """Popup window listing common keyboard shortcuts."""
        win = tk.Toplevel(self)
        win.title("Keyboard Shortcuts")
        win.transient(self)
        win.resizable(False, False)

        # basic padding frame
        body = ttk.Frame(win, padding=16)
        body.grid(row=0, column=0, sticky="nsew")

        # rows of "Action  |  Shortcut"
        shortcuts = [
            ("New file",            "Ctrl+N"),
            ("Open file…",          "Ctrl+O"),
            ("Save",                "Ctrl+S"),
            ("Render",              "Click Render / Auto render"),
            ("Undo",                "Ctrl+Z"),
            ("Redo",                "Ctrl+Y"),
            ("Cut",                 "Ctrl+X"),
            ("Copy",                "Ctrl+C"),
            ("Paste",               "Ctrl+V"),
            ("Select All",          "Ctrl+A"),
            ("Toggle Auto render",  "Click checkbox in toolbar"),
        ]

        # Title label
        ttk.Label(body, text="Keyboard Shortcuts", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w"
        )

        # Table-ish layout
        for idx, (action, combo) in enumerate(shortcuts, start=1):
            ttk.Label(body, text=action).grid(row=idx, column=0, sticky="w", padx=(0, 16), pady=2)
            ttk.Label(body, text=combo, foreground="#555").grid(row=idx, column=1, sticky="e", pady=2)

        # Close button
        btn_frame = ttk.Frame(body)
        btn_frame.grid(row=len(shortcuts) + 1, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(btn_frame, text="Close", command=win.destroy).grid(row=0, column=0, sticky="e")

        # make sure dialog is above main window and grabs focus
        win.grab_set()
        win.focus_force()


    def _open_mermaid_docs(self):
        """Open official Mermaid documentation in the user's default browser."""
        url = "https://docs.mermaidchart.com/mermaid-oss/intro/index.html"
        try:
            webbrowser.open(url)
            self._set_status("Opened Mermaid docs in browser")
        except Exception as e:
            messagebox.showerror("Error", f"Couldn't open browser:\n{e}")



    def _find_chrome(self) -> str | None:
        # 1. Puppeteer cache install
        try:
            cache = Path.home() / ".cache" / "puppeteer" / "chrome"
            if cache.exists():
                candidates = sorted(cache.glob("*/chrome-linux64/chrome"))
                if candidates:
                    return str(candidates[-1].resolve())
        except Exception:
            pass
        # 2. Common system locations
        for p in [
            "/usr/bin/google-chrome-stable",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
        ]:
            if Path(p).exists():
                return p
        return None



    def _render_async(self, input_file: Path, output_png: Path):
        if self.render_lock.locked():
            messagebox.showinfo("Rendering", "A render is already in progress.")
            return

        def worker():
            with self.render_lock:
                self._set_status("Rendering...")
                # Validate input exists and use absolute paths
                if not input_file.exists():
                    self._set_status("Input file missing")
                    messagebox.showerror("Render failed", f"Input file not found: {input_file}")
                    return

                # call mmdc (mermaid cli)
                bg_for_render = self.theme_manager.get_render_background()
                diagram_theme = self.theme_manager.get_diagram_theme()
                
                cmd = [
                self.mmdc_path,
                    "-i", str(input_file.resolve()),
                    "-o", str(output_png.resolve()),
                    "-b", bg_for_render,
                    "-w", "2048",
                    "--theme", diagram_theme,
                ]   

                config_path = Path.home() / ".config" / "mermaid_studio" / "puppeteer.json"
                if config_path.exists():
                    cmd += ["-p", str(config_path)]

                try:
                    # Run in the input file directory. Add a timeout so we do not hang forever.
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        check=False,
                        cwd=str(input_file.parent),
                        timeout=45,
                    )

                    # Check for any Mermaid parse/render errors, even if exit code is 0
                    soft_error = False
                    error_markers = [
                        "Syntax error in text",
                        "Parse error on line",
                        "Lexical error on line",
                        "Expecting '",         # mermaid's "Expecting 'X' got 'Y'" style
                    ]
                    combined_output = (result.stderr or "") + "\n" + (result.stdout or "")
                    for marker in error_markers:
                        if marker in combined_output:
                            soft_error = True
                            break

                    if result.returncode != 0 or soft_error:
                        items, summary, full_text = self._parse_mermaid_errors(result.stderr, result.stdout)
                        # Show in status bar
                        self._set_status(f"Render failed: {summary[:160]}")
                        # Highlite all errored lines
                        if items:
                            try:
                                self.editor.highlight_errors(items)
                            except Exception:
                                pass
                        self._errorlog_show(full_text)
                        return
                    if not output_png.exists():
                        raise RuntimeError("mmdc finished but no output PNG was produced")
                except subprocess.TimeoutExpired as te:
                    self._set_status("Render timed out")
                    messagebox.showerror(
                        "Render failed",
                        f"mmdc timed out after {te.timeout}s. \n \nCommand:\n{' '.join(cmd)}"
                    )
                    return
                except FileNotFoundError:
                    self._set_status("mmdc not found")
                    messagebox.showerror("Error", "mmdc not found. Set the path in Settings.")
                    return
                except Exception as e:
                    self._set_status("Render failed")
                    messagebox.showerror(
                        "Render failed",
                        f"{e}\n \nCommand:\n{' '.join(cmd)}\n \nInput:\n{input_file}\nOutput:\n{output_png}"
                    )
                    return


                # Clean temp input file if it was created by us
                try:
                    if str(input_file.name).startswith("mstudio_"):
                        input_file.unlink(missing_ok=True)
                except Exception:
                    pass
                self.last_png = output_png
                self.last_rendered_hash = self._code_hash_being_rendered
                self._set_status(f"Rendered to {output_png.name}")
                self.editor.clear_error_highlights()
                self._errorlog_hide()
                # Update preview
                try:
                    # If using PreviewPane
                    if hasattr(self, "preview"):
                        self.preview.display(output_png)
                    else:
                        self._show_preview(output_png)
                except Exception:
                    # Fall back to old method if needed
                    self._show_preview(output_png)

                # If edits happened during render and auto render is still on, schedule a quick follow-up
                if self.pending_autorender and self.auto_render_var.get():
                    self.pending_autorender = False
                    self._schedule_autorender(delay_ms=1000)



        threading.Thread(target=worker, daemon=True).start()

#    def _show_placeholder(self):
#        self.canvas.delete("all")
#        self.placeholder_text = self.canvas.create_text(
#            "150", "50",
#            text="No preview rendered yet",
#            fill="#888",
#            font=("Segoe UI", 14, "italic"),
#            anchor="center"
#        )


    # - Helpers
    def _show_preview(self, png_path: Path):
        try:
            img = Image.open(png_path)
        except Exception as e:
            messagebox.showerror("Preview error", f"Could not open PNG:\n{e}")
            return
        
        # Remove placeholder text once something is rendered
        #if hasattr(self, "placeholder_text"):
        #    self.canvas.delete(self.placeholder_text)

        # Fit image to canvas while preserving aspect ratio
        canvas_w = self.canvas.winfo_width() or 600
        canvas_h = self.canvas.winfo_height() or 400
        img_ratio = img.width / img.height
        canvas_ratio = canvas_w / canvas_h

        if img_ratio > canvas_ratio:
            new_w = min(img.width, canvas_w)
            new_h = int(new_w / img_ratio)
        else:
            new_h = min(img.height, canvas_h)
            new_w = int(new_h * img_ratio)

        preview = img.resize((max(1, new_w), max(1, new_h)), Image.LANCZOS)
        self.preview_img = ImageTk.PhotoImage(preview)  # keep reference
        self.canvas.delete("all")
        self.canvas.create_image(canvas_w // 2, canvas_h // 2, image=self.preview_img, anchor="center")
        self.canvas.update_idletasks()

    def _find_mmdc(self):
        # Find mmdc in PATH
        return shutil.which("mmdc")

    def _prompt_set_mmdc_path(self):
        if messagebox.askyesno("mmdc not found", "mermaid-cli (mmdc) was not found in PATH. Do you want to locate it?"):
            self._set_mmdc_path()
            return self.mmdc_path is not None
        return False

    def _set_mmdc_path(self):
        path = filedialog.askopenfilename(title="Select mmdc executable")
        if not path:
            return
        if not os.access(path, os.X_OK):
            messagebox.showerror("Invalid", "Selected file is not executable.")
            return
        self.mmdc_path = path
        self.status.configure(text=f"mmdc set to: {path}")

    def _set_title(self):
        name = self.current_file.name if self.current_file else "Untitled"
        self.title(f"{name} - {APP_TITLE}")

    def _set_status(self, text: str):
        self.status.configure(text=text)

    def _parse_mermaid_errors(self, stderr: str, stdout: str = ""):
        """
        Returns (items, message, full_text)
        items: list[(line:int, col:int|None)] for highlighting all lines
        message: short one-line summary
        full_text: detailed combined text for the error log
        We look for multiple '... error on line N ...' patterns and optional 'column C'.
        """
        full = ((stderr or "") + "\n" + (stdout or "")).strip()
        # Collect all line numbers
        lines = []
        for m in re.finditer(r"(?:Parse|Lexical)\s+error.*?line\s+(\d+)", full, re.IGNORECASE | re.DOTALL):
            try:
                lines.append(int(m.group(1)))
            except Exception:
                pass
        # Fallback: any 'line <num>' mentions
        if not lines:
            for m in re.finditer(r"\bline\s+(\d+)\b", full, re.IGNORECASE):
                try:
                    lines.append(int(m.group(1)))
                except Exception:
                    pass
        # Column: if present, we use the first one globally
        col = None
        mc = re.search(r"\bcolumn\s+(\d+)\b", full, re.IGNORECASE)
        if mc:
            try:
                col = int(mc.group(1))
            except Exception:
                pass

        # Deduplicate and sort
        uniq = sorted(set(lines))
        items = [(ln, col) for ln in uniq] if uniq else []

        # Short message for status
        lines_nonempty = [ln.strip() for ln in full.splitlines() if ln.strip()]
        summary = " | ".join(lines_nonempty[:3]) if lines_nonempty else "Mermaid render error"

        return items, summary, (full or "No error text")
    
    def _detect_diagram_type(self, code: str) -> str | None:
        """
        Heuristically guess the diagram type keyword from the first meaningful line.
        We skip blank lines and Mermaid comments (%% ...).
        Returns lowercase keyword like 'flowchart', 'sequenceDiagram' -> 'sequencediagram', etc.
        """
        for raw_line in code.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("%%"):
                continue

            # first token on the line (letters, digits, dash, underscore, dot)
            m = re.match(r"^([A-Za-z0-9_.:-]+)", line)
            if m:
                return m.group(1).lower()

        return None


    def _maybe_warn_diagram_type(self, code: str):
        """
        Decide if we should warn the user that this diagram type may not be supported
        by their installed Mermaid CLI yet. If so, we show that warning in the
        error log panel (non-fatal) BEFORE we actually render.
        """

        # This is our "known good / common" set for current CLI versions.
        # NOTE: All are stored lowercase.
        STABLE_TYPES = {
            "flowchart", "flowchart-lr", "flowchart-rl", "flowchart-tb", "flowchart-bt",
            "graph",
            "sequencediagram",
            "classdiagram",
            "statediagram", "statediagram-v2",
            "erdigram", "erdiagram",
            "journey",
            "gantt",
            "pie",
            "quadrantchart",
            "requirementdiagram",
            "gitgraph", "gitgraph",  # both spellings collapse to 'gitgraph' anyway after .lower()
            "c4context", "c4container", "c4component", "c4dynamic",
            "mindmap",
            "timeline",
            "sankey", "sankey-beta",
            "xychart", "xychart-beta",
            "blockdiagram",
            "packet",
            "kanban",
            "architecture",    # <-- newer/experimental in some Mermaid builds
            "radar",
            "treemap",
        }

        # Things that exist in Mermaid spec/docs but are still considered
        # experimental / version-sensitive. We'll gently warn on these.
        POTENTIALLY_UNSTABLE = {
            "architecture", "architecture-beta",
            "c4context", "c4container", "c4component", "c4dynamic",
            "quadrantchart",
            "sankey", "sankey-beta",
            "xychart", "xychart-beta",
            "kanban",
            "radar",
            "treemap", "treemap-beta"
            "blockdiagram",
        }

        dtype = self._detect_diagram_type(code)
        if dtype is None:
            # nothing meaningful found, don't warn
            return

        # Normalize some aliases so 'sequenceDiagram' becomes 'sequencediagram'
        # 'erDiagram' -> 'erdiagram', etc.
        # The _detect_diagram_type() already lowercased, so we're OK with lower comparisons.

        is_known = dtype in STABLE_TYPES
        is_unstable = dtype in POTENTIALLY_UNSTABLE

        # Three situations to warn the user:
        # 1. We don't even recognize this type at all.
        # 2. We recognize it but it's in POTENTIALLY_UNSTABLE, which often
        #    renders that "Syntax error in text" bomb even with exit code 0.
        if (not is_known) or is_unstable:
            if not is_known:
                msg = (
                    f"Diagram type '{dtype}' may not be supported by your Mermaid CLI.\n"
                    "If the preview shows a 'Syntax error in text' image, this is probably why."
                )
            else:
                # known, but flaky
                msg = (
                    f"Diagram type '{dtype}' is experimental / version-sensitive.\n"
                    "Your Mermaid CLI may render a 'Syntax error in text' banner instead of the diagram."
                )

            # show this in the error log panel WITHOUT calling it a failure
            self._errorlog_show(
                msg,
                status_msg="Warning: diagram type may not be fully supported"
            )


def main():
    app = MermaidStudio()
    app.mainloop()

if __name__ == "__main__":
    main()
