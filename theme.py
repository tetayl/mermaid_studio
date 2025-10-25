import os
import json
import tkinter as tk
from tkinter import ttk

LIGHT_THEME = {
    # window and panels
    "bg_main":      "#ffffff",
    "bg_panel":     "#f5f5f5",
    "border":       "#cfcfcf",

    # toolbar / status
    "toolbar_bg":   "#f5f5f5",
    "toolbar_fg":   "#000000",
    "status_fg":    "#000000",

    # preview background
    "preview_bg":   "#f5f5f5",
    "preview_fg":   "#555555",

    # error log
    "error_bg":     "#fff8f8",
    "error_fg":     "#7a0000",

    # editor (this plugs directly into MermaidEditor.set_theme)
    "editor": {
        "bg": "#ffffff",
        "fg": "#1e1e1e",
        "gutter_bg": "#f3f3f3",
        "gutter_fg": "#888888",
        "caret": "#000000",
        "select_bg": "#cce8ff",
        "select_fg": "#000000",
        "comment": "#6a9955",
        "directive": "#aa00aa",
        "keyword": "#0066cc",
        "type": "#b05a00",
        "string": "#a31515",
        "number": "#098658",
        "operator": "#333333",
        "arrow": "#0a7aca",
        "node": "#951db6",
        "error": "#ff0000",
        "current_line": "#f7faff",
        "match_bg": "#fff2a8",
    }
}

DARK_THEME = {
    "bg_main":      "#1e1e1e",
    "bg_panel":     "#252526",
    "border":       "#3c3c3c",

    "toolbar_bg":   "#252526",
    "toolbar_fg":   "#d4d4d4",
    "status_fg":    "#d4d4d4",

    "preview_bg":   "#1e1e1e",
    "preview_fg":   "#888888",

    "error_bg":     "#2b1a1a",
    "error_fg":     "#ff8f8f",

    "editor": {
        "bg": "#1e1e1e",
        "fg": "#d4d4d4",
        "gutter_bg": "#2a2a2a",
        "gutter_fg": "#777777",
        "caret": "#d4d4d4",
        "select_bg": "#264f78",
        "select_fg": "#ffffff",
        "comment": "#6a9955",
        "directive": "#d18ad1",
        "keyword": "#569cd6",
        "type": "#d7ba7d",
        "string": "#ce9178",
        "number": "#b5cea8",
        "operator": "#d4d4d4",
        "arrow": "#4fc1ff",
        "node": "#c586c0",
        "error": "#ff5555",
        "current_line": "#2a2d2e",
        "match_bg": "#3a3d41",
    }
}

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "mermaid_studio")
CONFIG_FILE = os.path.join(CONFIG_DIR, "theme.json")

def _load_saved_theme_name(default="light"):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            name = data.get("theme")
            if name in ("light", "dark"):
                return name
    except Exception:
        pass
    return default

def _save_theme_name(name: str):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"theme": name}, f)
    except Exception:
        pass


class ThemeManager:
    """
    Central theming controller.
    - Holds current theme name and dict
    - Knows about key widgets in MermaidStudio and can repaint them
    - Knows about the editor widget and preview widget
    """

    def __init__(self, app_root_tk):
        self.root = app_root_tk

        initial_name = _load_saved_theme_name(default="light")
        self.current_name = initial_name
        self.theme = self._theme_from_name(initial_name)

        # widgets we will paint
        self.toolbar = None          # ttk.Frame
        self.status_label = None     # ttk.Label
        self.editor_widget = None    # MermaidEditor
        self.err_text = None         # tk.Text
        self.err_frame = None        # ttk.Frame
        self.preview_widget = None   # PreviewPane outer widget (ttk.Frame or similar)

        # We'll also define a ttk.Style so ttk widgets inherit sane bg/fg in dark mode
        self.ttk_style = ttk.Style(self.root)

    def _theme_from_name(self, name: str):
        return DARK_THEME if name == "dark" else LIGHT_THEME

    def toggle_theme(self):
        self.set_theme("dark" if self.current_name == "light" else "light")

    def set_theme(self, name: str):
        self.current_name = name
        self.theme = self._theme_from_name(name)
        _save_theme_name(name)
        self.apply_theme()

    def get_render_background(self) -> str:
        # Return a color string usable for mmdc -b
        return self.theme["preview_bg"]


    def apply_theme(self):
        t = self.theme

        # Root window background
        self.root.configure(bg=t["bg_main"])

        # ttk styles. Note: tkinter's themed widgets can be stubborn on some platforms,
        # but we do best-effort.
        self.ttk_style.configure(
            "TFrame",
            background=t["bg_panel"],
        )
        self.ttk_style.configure(
            "TLabel",
            background=t["toolbar_bg"],
            foreground=t["toolbar_fg"],
        )
        self.ttk_style.configure(
            "StatusLabel.TLabel",
            background=t["toolbar_bg"],
            foreground=t["status_fg"],
        )
        self.ttk_style.configure(
            "TButton",
            background=t["bg_panel"],
            foreground=t["toolbar_fg"],
        )
        self.ttk_style.configure(
            "TCheckbutton",
            background=t["toolbar_bg"],
            foreground=t["toolbar_fg"],
        )
        self.ttk_style.configure(
            "TPanedwindow",
            background=t["bg_main"],
        )

        # Toolbar frame
        if self.toolbar is not None:
            self.toolbar.configure(style="TFrame")
            # force background on the raw tk side if needed
            try:
                self.toolbar.configure(background=t["toolbar_bg"])
            except tk.TclError:
                pass

        # Status label color specifically
        if self.status_label is not None:
            self.status_label.configure(style="StatusLabel.TLabel")

        # Error log: frame + text box
        if self.err_frame is not None:
            self.err_frame.configure(style="TFrame")
        if self.err_text is not None:
            # err_text is tk.Text, so configure directly
            self.err_text.configure(
                background=t["error_bg"],
                foreground=t["error_fg"],
                insertbackground=t["error_fg"],
                selectbackground="#444444" if self.current_name == "dark" else "#cce8ff",
                selectforeground="#ffffff" if self.current_name == "dark" else "#000000",
            )

        # Editor widget: call its public set_theme
        if self.editor_widget is not None:
            self.editor_widget.set_theme(t["editor"])

        # Preview widget background
        if self.preview_widget is not None:
            # Preview widget background
            if self.preview_widget is not None:
                try:
                    self.preview_widget.set_theme_colors(
                        bg_color=t["preview_bg"],
                        placeholder_fg=t["preview_fg"],
                        border_color=t["border"],
                    )
                except Exception:
                    # fallback if running against an older PreviewPane without theming hook
                    try:
                        self.preview_widget.configure(background=t["preview_bg"])
                    except Exception:
                        pass
                    try:
                        self.preview_widget.canvas.configure(background=t["preview_bg"])
                    except Exception:
                        pass
