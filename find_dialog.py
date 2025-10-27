# find_dialog.py
import tkinter as tk
from tkinter import ttk

class FindReplaceDialog(tk.Toplevel):
    def __init__(self, master, text_widget: tk.Text, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.title("Find / Replace")
        self.resizable(False, False)
        self.transient(master)  # stay on top-ish of main window

        self.text_widget = text_widget

        # state
        self.find_var = tk.StringVar()
        self.replace_var = tk.StringVar()

        # layout
        body = ttk.Frame(self, padding=8)
        body.grid(row=0, column=0, sticky="nsew")

        # Find row
        ttk.Label(body, text="Find:").grid(row=0, column=0, sticky="w")
        find_entry = ttk.Entry(body, textvariable=self.find_var, width=30)
        find_entry.grid(row=0, column=1, columnspan=3, sticky="we", pady=2)
        find_entry.focus_set()

        # Replace row
        ttk.Label(body, text="Replace:").grid(row=1, column=0, sticky="w")
        replace_entry = ttk.Entry(body, textvariable=self.replace_var, width=30)
        replace_entry.grid(row=1, column=1, columnspan=3, sticky="we", pady=2)

        # Buttons row
        btn_find = ttk.Button(body, text="Find Next", command=self._find_next)
        btn_find.grid(row=2, column=0, pady=(6, 0), sticky="we")

        btn_replace = ttk.Button(body, text="Replace", command=self._replace_one)
        btn_replace.grid(row=2, column=1, pady=(6, 0), sticky="we")

        btn_replace_all = ttk.Button(body, text="Replace All", command=self._replace_all)
        btn_replace_all.grid(row=2, column=2, pady=(6, 0), sticky="we")

        btn_close = ttk.Button(body, text="Close", command=self.destroy)
        btn_close.grid(row=2, column=3, pady=(6, 0), sticky="we")

        body.columnconfigure(1, weight=1)

        # tag for highlight
        self.text_widget.tag_configure("find_match", background="#fff59d")  # pale yellow

        # bindings: Enter triggers Find Next
        self.bind("<Return>", lambda e: self._find_next())
        self.bind("<Escape>", lambda e: self.destroy())

    def _clear_match_highlight(self):
        self.text_widget.tag_remove("find_match", "1.0", "end")

    def _find_next(self):
        needle = self.find_var.get()
        if not needle:
            return

        self._clear_match_highlight()

        # start searching right after the current insert cursor
        start_index = self.text_widget.index("insert +1c")

        # search forward
        idx = self.text_widget.search(
            pattern=needle,
            index=start_index,
            nocase=False,
            stopindex="end"
        )

        if not idx:
            # wrap: search from start
            idx = self.text_widget.search(
                pattern=needle,
                index="1.0",
                nocase=False,
                stopindex="end"
            )
            if not idx:
                return  # not found anywhere

        # idx is like "12.5"
        end_idx = f"{idx}+{len(needle)}c"

        # highlight selection
        self.text_widget.tag_add("sel", idx, end_idx)
        self.text_widget.tag_add("find_match", idx, end_idx)

        # move insert cursor and scroll into view
        self.text_widget.mark_set("insert", end_idx)
        self.text_widget.see(idx)

    def _replace_one(self):
        needle = self.find_var.get()
        repl = self.replace_var.get()
        if not needle:
            return

        try:
            sel_start = self.text_widget.index("sel.first")
            sel_end   = self.text_widget.index("sel.last")
        except tk.TclError:
            self._find_next()
            return

        selected_text = self.text_widget.get(sel_start, sel_end)
        if selected_text == needle:
            # perform replacement
            self.text_widget.delete(sel_start, sel_end)
            self.text_widget.insert(sel_start, repl)
            # after replace, move cursor to end of inserted text
            after_idx = f"{sel_start}+{len(repl)}c"
            self.text_widget.mark_set("insert", after_idx)
            self.text_widget.see(after_idx)

        # then jump to the next match
        self._find_next()

    def _replace_all(self):
        needle = self.find_var.get()
        repl = self.replace_var.get()
        if not needle:
            return

        self._clear_match_highlight()

        ranges = []
        idx = "1.0"
        while True:
            idx = self.text_widget.search(
                pattern=needle,
                index=idx,
                nocase=False,
                stopindex="end"
            )
            if not idx:
                break
            end_idx = f"{idx}+{len(needle)}c"
            ranges.append((idx, end_idx))
            idx = end_idx  # continue search after this match

        # Now perform replacements from bottom up so indices don't shift
        for start, end in reversed(ranges):
            self.text_widget.delete(start, end)
            self.text_widget.insert(start, repl)

        if ranges:
            last_start, _ = ranges[-1]
            after_last = f"{last_start}+{len(repl)}c"
            self.text_widget.mark_set("insert", after_last)
            self.text_widget.see(after_last)
