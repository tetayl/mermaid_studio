# code_editor.py
# Mermaid-aware Tkinter editor widget with syntax highlighting and line numbers.
# Public API:
#   class MermaidEditor(tk.Frame)
#       .get() -> str
#       .set_text(text: str) -> None
#       .focus_editor() -> None
#       .on_change(callback) -> None            # called after user edits pause
#       .set_theme(theme_dict) -> None          # optional color overrides
#
# Usage example in your main file:
#   from code_editor import MermaidEditor
#   editor = MermaidEditor(parent)
#   editor.pack(fill="both", expand=True)
#
# Dependencies: standard library + Tkinter (no external packages)

from __future__ import annotations
import re
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

# Default light theme
DEFAULT_THEME = {
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

MERMAID_KEYWORDS = r"\b(graph|flowchart|flowchart-(LR|RL|TB|BT)|sequenceDiagram|classDiagram|stateDiagram|stateDiagram-v2|erDiagram|gantt|journey|pie|mindmap|timeline|gitGraph|architecture-beta|quadrantChart|radar|radar-beta|sankey|sankey-beta|treemap|treemap-beta|C4Context|zenuml)\b"
MERMAID_TYPES = r"\b(subgraph|end|click|style|linkStyle|accTitle|accDescr|activate|deactivate|autonumber|dateFormat|axisFormat|section|participant|Note|classDef|direction|title|loop|alt|opt|par|rect|else)\b"

# Arrows and edge operators commonly used in Mermaid
ARROWS = r"(-->|==>|===|->|<-|<->|--x|x--|--o|o--|--\||\|--|==|--|\.\.|:::)"
# Node-like delimiters for highlighting labels quickly: [label], (label), ((label)), {label}, [[label]]
NODE_DELIMS = r"(\[\[.*?\]\]|\[.*?\]|\(\(.*?\)\)|\([^()\n]*\)|\{[^{}\n]*\})"

# Simple token patterns
TOKENS = [
    ("comment", re.compile(r"%%.*?$", re.MULTILINE)),
    ("directive", re.compile(r"%%\{.*?}%%", re.DOTALL)),
    ("keyword", re.compile(MERMAID_KEYWORDS, re.IGNORECASE)),
    ("type", re.compile(MERMAID_TYPES, re.IGNORECASE)),
    ("string", re.compile(r"(?P<q>['\"]).*?(?P=q)")),
    ("number", re.compile(r"\b\d+(?:\.\d+)?\b")),
    ("arrow", re.compile(ARROWS)),
    ("node", re.compile(NODE_DELIMS)),
    ("operator", re.compile(r"[:=+/*<>!|.,]")),
]

class LineNumbers(tk.Canvas):
    def __init__(self, master, text_widget: tk.Text, theme: dict):
        super().__init__(master, width=48, highlightthickness=0, bg=theme["gutter_bg"])
        self.text_widget = text_widget
        self.theme = theme
        self.text_widget.bind("<<Change>>", self._on_change, add=True)
        self.text_widget.bind("<Configure>", self._on_change, add=True)
        self.text_widget.bind("<MouseWheel>", self._on_change, add=True)           # Windows
        self.text_widget.bind("<Button-4>", self._on_change, add=True)             # Linux scroll up
        self.text_widget.bind("<Button-5>", self._on_change, add=True)             # Linux scroll down

    def _on_change(self, event=None):
        self.redraw()

    def redraw(self):
        self.delete("all")
        i = self.text_widget.index("@0,0")
        last_index = self.text_widget.index("end-1c")
        while True:
            dline = self.text_widget.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            line_no = str(i).split(".")[0]
            self.create_text(44, y, anchor="ne", text=line_no, font=("Courier New", 11),
                             fill=self.theme["gutter_fg"])
            i = self.text_widget.index(f"{i}+1line")
            if self.text_widget.compare(i, ">=", last_index):
                break

class MermaidEditor(tk.Frame):
    def __init__(self, master, theme: Optional[dict] = None):
        super().__init__(master)
        self.theme = dict(DEFAULT_THEME)
        if theme:
            self.theme.update(theme)

        self._change_callback: Optional[Callable[[], None]] = None
        self._highlight_scheduled = False
        self._change_scheduled = False

        self._build_ui()
        self._configure_tags()
        self._bind_keys()

        # initial highlight
        self.after(50, self.highlight_visible)

    # Public API
    def get(self) -> str:
        return self.text.get("1.0", "end-1c")

    def set_text(self, text: str) -> None:
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text)
        self._schedule_highlight()

    def focus_editor(self) -> None:
        self.text.focus_set()

    def on_change(self, callback: Callable[[], None]) -> None:
        self._change_callback = callback

    def set_theme(self, theme: dict) -> None:
        self.theme.update(theme)
        self._apply_theme()

    # UI
    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Text widget with scrollbars
        self.v_scroll = ttk.Scrollbar(self, orient="vertical")
        self.h_scroll = ttk.Scrollbar(self, orient="horizontal")

        self.text = tk.Text(
            self,
            wrap="none",
            undo=True,
            background=self.theme["bg"],
            foreground=self.theme["fg"],
            insertbackground=self.theme["caret"],
            selectbackground=self.theme["select_bg"],
            selectforeground=self.theme["select_fg"],
            font=("Courier New", 12),
            padx=6,
            pady=6,
            tabs=("32"),  # visual tab width
        )
        self.text.config(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        self.v_scroll.config(command=self.text.yview)
        self.h_scroll.config(command=self.text.xview)

        # Line numbers
        self.linenos = LineNumbers(self, self.text, self.theme)

        # Layout
        self.linenos.grid(row=0, column=0, sticky="nsw")
        self.text.grid(row=0, column=1, sticky="nsew")
        self.v_scroll.grid(row=0, column=2, sticky="ns")
        self.h_scroll.grid(row=1, column=0, columnspan=3, sticky="ew")

        # Tag for current line background
        self.text.tag_configure("current_line", background=self.theme["current_line"])

        # Event for line number updates
        self.text.bind("<<Modified>>", self._on_modified_flag, add=True)
        self.text.bind("<KeyRelease>", lambda e: self._event_changed(), add=True)
        self.text.bind("<ButtonRelease-1>", lambda e: self._event_changed(), add=True)
        self.text.bind("<MouseWheel>", lambda e: self._event_changed(), add=True)
        self.text.bind("<Button-4>", lambda e: self._event_changed(), add=True)
        self.text.bind("<Button-5>", lambda e: self._event_changed(), add=True)

    def _apply_theme(self):
        self.configure(bg=self.theme["bg"])
        self.text.configure(
            background=self.theme["bg"],
            foreground=self.theme["fg"],
            insertbackground=self.theme["caret"],
            selectbackground=self.theme["select_bg"],
            selectforeground=self.theme["select_fg"],
        )
        self.linenos.configure(bg=self.theme["gutter_bg"])
        # Update tag colors
        self._configure_tags()
        self._schedule_highlight()

    def _configure_tags(self):
        t = self.text
        t.tag_configure("comment", foreground=self.theme["comment"])
        t.tag_configure("directive", foreground=self.theme["directive"])
        t.tag_configure("keyword", foreground=self.theme["keyword"])
        t.tag_configure("type", foreground=self.theme["type"])
        t.tag_configure("string", foreground=self.theme["string"])
        t.tag_configure("number", foreground=self.theme["number"])
        t.tag_configure("operator", foreground=self.theme["operator"])
        t.tag_configure("arrow", foreground=self.theme["arrow"])
        t.tag_configure("node", foreground=self.theme["node"])
        t.tag_configure("error", foreground=self.theme["error"], underline=True)
        t.tag_configure("syntax_error_line", background="#ffecec")   # light red line tint
        t.tag_configure("syntax_error_col", underline=True, foreground="#d00")


    # Change and highlight scheduling
    def _on_modified_flag(self, event=None):
        # Reset Tk modified flag and trigger events
        self.text.tk.call(self.text._w, "edit", "modified", 0)
        self._event_changed()

    def _event_changed(self):
        self._schedule_highlight()
        self._schedule_change_callback()
        self.linenos.redraw()
        self._paint_current_line()
        self._highlight_bracket_match()

    def _schedule_highlight(self):
        if not self._highlight_scheduled:
            self._highlight_scheduled = True
            self.after(80, self.highlight_visible)

    def _schedule_change_callback(self):
        if not self._change_scheduled:
            self._change_scheduled = True
            self.after(250, self._emit_change)

    def _emit_change(self):
        self._change_scheduled = False
        if self._change_callback:
            self._change_callback()

    # Highlighting
    def highlight_visible(self):
        self._highlight_scheduled = False
        text = self.text

        # Determine visible region to limit work
        first = text.index("@0,0")
        last = text.index("@0,%d" % (text.winfo_height()))
        start_line = int(first.split(".")[0])
        end_line = int(last.split(".")[0]) + 1
        region_start = f"{start_line}.0"
        region_end = f"{end_line}.0"

        # Clear token tags in region
        for tag in ("comment", "directive", "keyword", "type", "string",
                    "number", "operator", "arrow", "node", "error"):
            text.tag_remove(tag, region_start, region_end)

        segment = text.get(region_start, region_end)

        # Apply patterns
        for tag, pattern in TOKENS:
            for m in pattern.finditer(segment):
                s, e = m.span()
                s_idx = self._index_add(region_start, s, segment)
                e_idx = self._index_add(region_start, e, segment)
                text.tag_add(tag, s_idx, e_idx)

        # Simple error underline for unclosed quotes on the visible lines
        self._highlight_unclosed_strings(segment, region_start)

    def _index_add(self, start_index: str, offset: int, text_segment: str) -> str:
        # Convert byte-offset like span to Tk index relative to region_start
        # Count newlines up to offset, compute column in last line
        upto = text_segment[:offset]
        line = upto.count("\n")
        if line == 0:
            col = len(upto)
        else:
            col = len(upto.split("\n")[-1])
        base_line = int(start_index.split(".")[0])
        return f"{base_line + line}.{col}"

    def _highlight_unclosed_strings(self, segment: str, region_start: str):
        # Detect odd counts of quotes on a line. Quick heuristic.
        lines = segment.split("\n")
        line_no = int(region_start.split(".")[0])
        for i, line in enumerate(lines):
            # Count quotes that are not escaped
            dq = len(re.findall(r'(?<!\\)"', line))
            sq = len(re.findall(r"(?<!\\)'", line))
            if dq % 2 == 1 or sq % 2 == 1:
                s_idx = f"{line_no + i}.0"
                e_idx = f"{line_no + i}.end"
                self.text.tag_add("error", s_idx, e_idx)

    # Current line background
    def _paint_current_line(self):
        self.text.tag_remove("current_line", "1.0", "end")
        cur = self.text.index("insert").split(".")[0]
        self.text.tag_add("current_line", f"{cur}.0", f"{cur}.0 lineend+1c")

    # Bracket match highlight for (), [], {}
    def _highlight_bracket_match(self):
        self.text.tag_remove("match", "1.0", "end")
        self.text.tag_configure("match", background=self.theme["match_bg"])
        idx = self.text.index("insert")
        prev = self.text.get(f"{idx} -1c")
        pairs = {"(": ")", "[": "]", "{": "}"}
        revpairs = {")": "(", "]": "[", "}": "{"}
        if prev in pairs:
            match = self._find_matching_forward(idx + " -1c", prev, pairs[prev])
            if match:
                self.text.tag_add("match", idx + " -1c", idx)
                self.text.tag_add("match", match, f"{match} +1c")
        elif prev in revpairs:
            match = self._find_matching_backward(idx + " -1c", prev, revpairs[prev])
            if match:
                self.text.tag_add("match", idx + " -1c", idx)
                self.text.tag_add("match", match, f"{match} +1c")

    def _find_matching_forward(self, start, open_ch, close_ch):
        depth = 0
        i = self.text.index(start)
        end = self.text.index("end-1c")
        while self.text.compare(i, "<", end):
            ch = self.text.get(i)
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    return i
            i = self.text.index(f"{i} +1c")
        return None

    def _find_matching_backward(self, start, close_ch, open_ch):
        depth = 0
        i = self.text.index(start)
        while self.text.compare(i, ">", "1.0"):
            ch = self.text.get(i)
            if ch == close_ch:
                depth += 1
            elif ch == open_ch:
                depth -= 1
                if depth == 0:
                    return i
            i = self.text.index(f"{i} -1c")
        return None

    # Key bindings: indent, outdent, tab handling, comment toggle, basic auto indent
    def _bind_keys(self):
        t = self.text
        t.bind("<Tab>", self._indent_selection)
        t.bind("<ISO_Left_Tab>", self._outdent_selection)   # Shift+Tab on some layouts
        t.bind("<Shift-Tab>", self._outdent_selection)
        t.bind("<Return>", self._auto_indent_newline)

        # Robust Ctrl+/ (toggle comment) across layouts/platforms
        comment_bindings = (
            "<Control-/>",          # works on many
            "<Control-slash>",      # explicit keysym
            "<Control-Key-/>",      # some Tk builds
            "<Control-underscore>", # common physical key with Shift on some layouts
            "<Command-/>",          # macOS Command+/ if you ever run on mac
            "<Meta-/>",             # some mac Tk variants
        )
        for seq in comment_bindings:
            try:
                t.bind(seq, self._toggle_comment)
            except tk.TclError:
                pass  # silently skip unsupported sequences

        # mark modified to trigger <<Modified>>
        def _key(event):
            self.text.event_generate("<<Change>>")
            return None
        t.bind("<Key>", _key, add=True)

    def _get_selection_lines(self):
        t = self.text
        try:
            start = t.index("sel.first")
            end = t.index("sel.last")
        except tk.TclError:
            cur = t.index("insert")
            return int(cur.split(".")[0]), int(cur.split(".")[0])
        return int(start.split(".")[0]), int(end.split(".")[0])

    def _indent_selection(self, event=None):
        t = self.text
        first, last = self._get_selection_lines()
        for line in range(first, last + 1):
            t.insert(f"{line}.0", "    ")
        return "break"

    def _outdent_selection(self, event=None):
        t = self.text
        first, last = self._get_selection_lines()
        for line in range(first, last + 1):
            start = f"{line}.0"
            leading = t.get(start, f"{line}.4")
            if leading.startswith("    "):
                t.delete(start, f"{line}.4")
            elif leading.startswith("\t"):
                t.delete(start, f"{line}.1")
        return "break"

    def _auto_indent_newline(self, event=None):
        t = self.text
        cur = t.index("insert")
        line_start = f"{cur.split('.')[0]}.0"
        current_line = t.get(line_start, f"{line_start} lineend")
        indent = re.match(r"[ \t]*", current_line).group(0)
        t.insert("insert", "\n" + indent)
        return "break"

    def _toggle_comment(self, event=None):
        # Mermaid comments start with %%
        t = self.text
        first, last = self._get_selection_lines()
        # Detect if every line already commented
        lines = [t.get(f"{ln}.0", f"{ln}.end") for ln in range(first, last + 1)]
        all_commented = all(l.strip().startswith("%%") or l.strip() == "" for l in lines)
        for i, ln in enumerate(range(first, last + 1)):
            line_text = lines[i]
            if all_commented:
                # remove %%
                m = re.match(r"[ \t]*%%[ ]?", line_text)
                if m:
                    start = f"{ln}.0+{m.start()}c"
                    end = f"{ln}.0+{m.end()}c"
                    t.delete(start, end)
            else:
                # add %%
                lead = re.match(r"[ \t]*", line_text).group(0)
                t.insert(f"{ln}.0+{len(lead)}c", "%% ")
        return "break"
    
    def clear_error_highlights(self) -> None:
        self.text.tag_remove("syntax_error_line", "1.0", "end")
        self.text.tag_remove("syntax_error_col", "1.0", "end")

    def highlight_error(self, line: int, col: int | None = None, length: int = 1) -> None:
        ln = max(1, int(line))
        self.text.tag_add("syntax_error_line", f"{ln}.0", f"{ln}.0 lineend+1c")
        if col is not None:
            c0 = max(0, int(col) - 1)
            self.text.tag_add("syntax_error_col", f"{ln}.{c0}", f"{ln}.{c0+max(1,int(length))}")

    def highlight_errors(self, items: list[tuple[int, int | None]]) -> None:
        """
        items: list of (line, col|None)
        Highlights all; scrolls to the first one and puts caret there.
        """
        if not items:
            return
        self.clear_error_highlights()
        for (line, col) in items:
            self.highlight_error(line, col)
        ln, col = items[0]
        self.text.see(f"{max(1,int(ln))}.0")
        self.text.mark_set("insert", f"{max(1,int(ln))}.{max(0,(0 if col is None else col-1))}")
        self.text.focus_set()



# Quick manual test
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Mermaid Editor Demo")
    root.geometry("900x600")
    editor = MermaidEditor(root)
    editor.pack(fill="both", expand=True)
    editor.set_text("""%%{init: {'theme': 'base'}}%%
flowchart LR
    A[Objective] --> B(Steps)
    B --> C{Expected result}
    C -->|ok| D[Done]
    C -->|fail| E((Retry))
""")
    root.mainloop()
