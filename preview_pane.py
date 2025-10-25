# preview_pane.py
# A self-contained Tkinter preview pane with zoom, pan, and reset-to-fit.
# Dependencies: Pillow (PIL)

from __future__ import annotations
from pathlib import Path
from typing import Optional
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk


class PreviewPane(tk.Frame):
    """
    Drop-in preview widget.

    Public API:
      - display(image_path: str | Path) -> None
      - set_placeholder(text: str = "No preview rendered yet") -> None
      - reset_view() -> None
      - canvas  (tk.Canvas)  - kept for compatibility if you accessed it directly

    Usage:
        preview = PreviewPane(parent)
        preview.grid(row=0, column=0, sticky="nsew")
        preview.display("/path/to/image.png")
    """

    def __init__(self, master, *, bg="#f5f5f5"):
        super().__init__(master, background=bg)
        self.bg = bg
        self.placeholder_fg = "#888"  # default light grey for placeholder text

        # Layout
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # Canvas
        self.canvas = tk.Canvas(self, background=bg, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # Reset button (top-right overlay)
        self.btn_reset = ttk.Button(self, text="⟲", width=2, command=self.reset_view)
        self.btn_reset.place(relx=1.0, rely=0.0, anchor="ne", x=-8, y=8)
        self.btn_reset.lower(self.canvas)

        # Internal state
        self._src_image: Optional[Image.Image] = None   # original PIL image
        self._photo: Optional[ImageTk.PhotoImage] = None
        self._img_item: Optional[int] = None
        self._zoom: float = 1.0
        self._fit_zoom: float = 1.0
        self._min_zoom: float = 0.05
        self._max_zoom: float = 8.0

        # Panning
        self._pan_start: Optional[tuple[int, int]] = None

        # Placeholder
        self._placeholder_id: Optional[int] = None
        self.set_placeholder("No preview rendered yet")

        # Events
        self.canvas.bind("<Configure>", self._on_resize, add=True)

        # Mouse wheel zoom: Windows/macOS
        self.canvas.bind("<MouseWheel>", self._on_mousewheel_zoom, add=True)
        # Mouse wheel zoom: Linux
        self.canvas.bind("<Button-4>", lambda e: self._zoom_at(1.10, e.x, e.y), add=True)
        self.canvas.bind("<Button-5>", lambda e: self._zoom_at(0.90, e.x, e.y), add=True)

        # Pan with left button drag
        self.canvas.bind("<ButtonPress-1>", self._pan_start_evt, add=True)
        self.canvas.bind("<B1-Motion>", self._pan_move_evt, add=True)

    # Public API ---------------------------------------------------------------

    def display(self, image_path: str | Path) -> None:
        # (unchanged)
        path = Path(image_path)
        self._src_image = Image.open(path).convert("RGBA")
        self._clear_placeholder()
        self._fit_to_window()
        self._render_image()
        self.btn_reset.lift()

    def set_placeholder(self, text: str = "No preview rendered yet") -> None:
        self.canvas.delete("all")
        self._img_item = None
        self._photo = None
        self._placeholder_id = self.canvas.create_text(
            self.canvas.winfo_width() // 2 or 200,
            self.canvas.winfo_height() // 2 or 120,
            text=text,
            fill=self.placeholder_fg,  # use current theme's placeholder fg
            font=("Segoe UI", 14, "italic"),
            anchor="center",
        )
        self.btn_reset.lower(self.canvas)

    def reset_view(self) -> None:
        """Reset zoom and center to fit."""
        if self._src_image is None:
            return
        self._fit_to_window()
        self._render_image()

    def set_theme_colors(self, bg_color: str, placeholder_fg: str, border_color: str) -> None:
        """
        Called by ThemeManager when theme changes.
        bg_color: preview background
        placeholder_fg: text color for 'No preview yet'
        border_color: outline color around preview frame (optional aesthetic)
        """
        self.bg = bg_color
        self.placeholder_fg = placeholder_fg

        # Frame background
        self.configure(background=bg_color, highlightthickness=1, highlightbackground=border_color)

        # Canvas background
        self.canvas.configure(background=bg_color)

        # Reset button style we leave to ttk themeing, so nothing here.

        # If we're currently showing the placeholder text (no image displayed),
        # redraw placeholder so it picks up the new placeholder_fg.
        if self._src_image is None:
            self.set_placeholder("No preview rendered yet")
        else:
            # we do have an image, so just force a re-render to clear any highlight mismatch
            self._render_image()

    # Internal helpers ---------------------------------------------------------

    def _clear_placeholder(self):
        if self._placeholder_id is not None:
            self.canvas.delete(self._placeholder_id)
            self._placeholder_id = None

    def _on_resize(self, event=None):
        # When the canvas resizes, recompute fit zoom and re-render if we are at fit
        if self._src_image is None:
            # keep placeholder centered
            if self._placeholder_id is not None:
                self.canvas.coords(
                    self._placeholder_id,
                    self.canvas.winfo_width() // 2,
                    self.canvas.winfo_height() // 2,
                )
            return
        prev_is_fit = abs(self._zoom - self._fit_zoom) < 1e-6
        self._fit_zoom = self._compute_fit_zoom()
        if prev_is_fit:
            self._zoom = self._fit_zoom
            self._render_image()
        else:
            # Canvas size changed but we keep current zoom; just re-render to new size
            self._render_image()

    def _compute_fit_zoom(self) -> float:
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        iw, ih = self._src_image.size
        return max(self._min_zoom, min(1.0 * cw / iw, 1.0 * ch / ih))

    def _fit_to_window(self):
        self._fit_zoom = self._compute_fit_zoom()
        self._zoom = self._fit_zoom

    def _render_image(self):
        if self._src_image is None:
            return
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        iw, ih = self._src_image.size
        sw = max(1, int(iw * self._zoom))
        sh = max(1, int(ih * self._zoom))
        img = self._src_image.resize((sw, sh), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(img)

        self.canvas.delete("all")
        self._img_item = self.canvas.create_image(cw // 2, ch // 2, image=self._photo, anchor="center")
        # Bring reset button to front
        self.btn_reset.lift()

    # Zoom and pan -------------------------------------------------------------

    def _on_mousewheel_zoom(self, event):
        # Positive delta on Windows/mac is zoom in
        if event.delta > 0:
            self._zoom_at(1.10, event.x, event.y)
        elif event.delta < 0:
            self._zoom_at(0.90, event.x, event.y)

    def _zoom_at(self, factor: float, x: int, y: int):
        if self._src_image is None:
            return

        new_zoom = min(self._max_zoom, max(self._min_zoom, self._zoom * factor))
        if abs(new_zoom - self._zoom) < 1e-6:
            return

        # Compute pan to keep the point under cursor stable
        # Current image center on canvas
        cx, cy = self._get_image_center()
        # Vector from center to cursor
        dx = x - cx
        dy = y - cy
        ratio = new_zoom / self._zoom

        # Update zoom and re-render
        self._zoom = new_zoom
        self._render_image()

        # After re-render, move image so that the same relative point stays under cursor
        nx, ny = self._get_image_center()
        # Desired new center so that (x,y) remains stable
        target_cx = x - dx * ratio
        target_cy = y - dy * ratio
        self.canvas.move(self._img_item, target_cx - nx, target_cy - ny)

    def _get_image_center(self):
        if self._img_item is None:
            return (self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2)
        x, y = self.canvas.coords(self._img_item)
        return (int(x), int(y))

    def _pan_start_evt(self, event):
        if self._img_item is None:
            return
        self._pan_start = (event.x, event.y)

    def _pan_move_evt(self, event):
        if self._img_item is None or self._pan_start is None:
            return
        sx, sy = self._pan_start
        dx, dy = event.x - sx, event.y - sy
        self.canvas.move(self._img_item, dx, dy)
        self._pan_start = (event.x, event.y)


# Manual test
if __name__ == "__main__":
    root = tk.Tk()
    root.title("PreviewPane demo")
    root.geometry("900x600")
    pane = PreviewPane(root)
    pane.pack(fill="both", expand=True)
    # pane.display("example.png")  # set a path to test
    root.mainloop()
