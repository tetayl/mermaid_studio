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



APP_VERSION = "0.2.1"

APP_TITLE = "Mermaid Studio - Python UI"
DEFAULT_SAMPLE = """flowchart LR
    A[Objective] --> B[Steps]
    B[Steps] --> C[Expected result]
    C[Expected result] --> D[Severity if failed]
"""

class MermaidStudio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry("1200x700")
        self.minsize(800, 500)
        self.chrome_path: str | None = self._find_chrome()


        # State
        self.current_file: Path | None = None
        self.last_png: Path | None = None
        self.mmdc_path: str | None = self._find_mmdc()
        self.render_lock = threading.Lock()

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

        # Menu
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", command=self._new_document, accelerator="Ctrl+N")
        file_menu.add_command(label="Open...", command=self._open_file, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Save", command=self._save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self._save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Export PNG As...", command=self._export_png_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        # Examples menu (between File and Settings)
        examples_menu = tk.Menu(menubar, tearoff=0)
        for name in sorted(list_examples()):
            examples_menu.add_command(
                label=name,
                command=lambda n=name: self._apply_example(n)
            )
        menubar.add_cascade(label="Examples", menu=examples_menu)


        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Set mmdc path...", command=self._set_mmdc_path)
        settings_menu.add_command(label="About", command=self._about)
        menubar.add_cascade(label="Settings", menu=settings_menu)

        self.config(menu=menubar)

        # Toolbar
        toolbar = ttk.Frame(self, padding=(6, 4))
        toolbar.grid(row=0, column=0, sticky="ew")   # grid is fine here (toolbar in root)

        # Left-aligned controls
        self.render_btn = ttk.Button(toolbar, text="Render", command=self._render_clicked)
        self.render_btn.pack(side="left", padx=(0, 8))

        self.auto_cb = ttk.Checkbutton(
            toolbar, text="Auto render", variable=self.auto_render_var,
            command=self._on_autorender_toggle
        )
        self.auto_cb.pack(side="left")

        # Right-aligned status
        self.status = ttk.Label(toolbar, text="Ready", anchor="e")
        self.status.pack(side="right")

        # Paned window: editor | preview
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.grid(row=1, column=0, sticky="nsew")

        # Editor (Mermaid-aware)
        editor_frame = ttk.Frame(paned)
        editor_frame.rowconfigure(0, weight=1)
        editor_frame.columnconfigure(0, weight=1)

        self.editor = MermaidEditor(editor_frame)
        self.editor.grid(row=0, column=0, sticky="nsew")

        # Optional: react to changes (e.g., show Edited in status bar)
        self.editor.on_change(self._on_editor_changed)


        paned.add(editor_frame, weight=1)

        # Preview
        preview_frame = ttk.Frame(paned)
        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)

        # old
        #self.canvas = tk.Canvas(preview_frame, background="#f5f5f5")
        #self.canvas.grid(row=0, column=0, sticky="nsew")
        from preview_pane import PreviewPane
        self.preview = PreviewPane(preview_frame, bg="#f5f5f5")
        self.preview.grid(row=0, column=0, sticky="nsew")
        #self.preview.set_placeholder("No preview rendered yet")

        paned.add(preview_frame, weight=1)
        # Set divider to 50% once the window has been drawn
        self.after(100, lambda: paned.sashpos(0, self.winfo_width() // 3))

        # Add placeholder text in the center of the preview pane
        #self.placeholder_text = self.canvas.create_text(
        #    "150", "50",
        #    text="No preview rendered yet",
        #    fill="#888",
        #    font=("Segoe UI", 14, "italic"),
        #    anchor="center"
        #)

        # Key bindings
        self.bind_all("<Control-n>", lambda e: self._new_document())
        self.bind_all("<Control-o>", lambda e: self._open_file())
        self.bind_all("<Control-s>", lambda e: self._save_file())

    def _on_editor_changed(self):
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
        self.current_file = None
        self._set_title()
        self.editor.set_text((initial_text.strip() + "\n \n") if initial_text else "")
        self.status.configure(text="New document")
        self.editor.focus_editor()

    def _open_file(self):
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
            self.status.configure(text=f"Opened {Path(path).name}")
            self.editor.focus_editor()
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{e}")

    def _save_file(self, force_dialog: bool = False):
        if self.current_file is None or force_dialog:
            return self._save_file_as()
        try:
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(self.editor.get())
            self.status.configure(text=f"Saved {self.current_file.name}")
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
        return self._save_file()

    def _export_png_as(self):
        if self.last_png is None or not self.last_png.exists():
            messagebox.showwarning("No PNG yet", "Please render first to generate a PNG.")
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

        # Write under $HOME/mermaid_studio_cache so the Snap can read it
        cache_dir = Path.home() / "mermaid_studio_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        import uuid
        temp_input_path = cache_dir / f"mstudio_{uuid.uuid4().hex}.mmd"
        with open(temp_input_path, "w", encoding="utf-8") as f:
            f.write(code)
        # Ensure readable by confined processes
        os.chmod(temp_input_path, 0o644)

        # If a document is saved, render PNG next to it. Otherwise, use cache path
        if self.current_file:
            out_dir = self.current_file.parent
            out_png = out_dir / (self.current_file.stem + ".png")
        else:
            out_png = cache_dir / f"mstudio_{uuid.uuid4().hex}.png"

        self._render_async(input_file=temp_input_path, output_png=out_png)


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

                cmd = [self.mmdc_path, "-i", str(input_file.resolve()), "-o", str(output_png.resolve())]
                cmd = [self.mmdc_path, "-i", str(input_file.resolve()), "-o", str(output_png.resolve())]
                cmd += ["-b", "white", "-w", "2048"]
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
                    if result.returncode != 0:
                        # Surface whatever mmdc printed
                        msg = result.stderr.strip() or result.stdout.strip() or "mmdc returned a nonzero exit status"
                        raise RuntimeError(msg)
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

def main():
    app = MermaidStudio()
    app.mainloop()

if __name__ == "__main__":
    main()
