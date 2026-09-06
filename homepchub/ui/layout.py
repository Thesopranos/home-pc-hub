"""Window sizing helpers - keep dialogs on-screen with usable chrome."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def size_window(
    win: tk.Misc,
    width: int,
    height: int,
    *,
    min_width: int | None = None,
    min_height: int | None = None,
) -> None:
    """Set geometry capped to the working screen (taskbar margin)."""
    win.update_idletasks()
    try:
        sw = int(win.winfo_screenwidth())
        sh = int(win.winfo_screenheight())
    except tk.TclError:
        sw, sh = 1280, 800
    max_w = max(320, sw - 48)
    max_h = max(360, sh - 96)
    w = max(280, min(int(width), max_w))
    h = max(280, min(int(height), max_h))
    win.geometry(f"{w}x{h}")
    if min_width and min_height:
        win.minsize(min(min_width, w), min(min_height, h))


class ThemedVScrollbar(tk.Canvas):
    """Flat vertical scrollbar that always matches theme tokens (Windows-safe)."""

    def __init__(self, parent: tk.Misc, theme: dict, *, command=None, width: int = 10):
        super().__init__(
            parent,
            width=width,
            highlightthickness=0,
            bd=0,
            bg=theme["surface"],
            cursor="arrow",
        )
        self._command = command
        self._theme = theme
        self._width = width
        self._lo = 0.0
        self._hi = 1.0
        self._dragging = False
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Button-1>", self._on_down)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_up)

    def set_theme(self, theme: dict) -> None:
        self._theme = theme
        self.configure(bg=theme["surface"])
        self._draw()

    def set(self, lo, hi) -> None:  # ttk.Scrollbar API
        try:
            self._lo = float(lo)
            self._hi = float(hi)
        except (TypeError, ValueError):
            self._lo, self._hi = 0.0, 1.0
        self._draw()

    def _thumb_metrics(self):
        h = max(1, self.winfo_height())
        span = max(0.05, min(1.0, self._hi - self._lo))
        thumb_h = max(24, int(h * span))
        travel = max(0, h - thumb_h)
        y0 = int(self._lo * travel) if travel else 0
        return y0, thumb_h, h

    def _draw(self) -> None:
        self.delete("all")
        y0, thumb_h, h = self._thumb_metrics()
        w = self._width
        trough = self._theme["surface"]
        thumb = (
            self._theme["border_strong"] if self._dragging else self._theme["border"]
        )
        self.create_rectangle(0, 0, w, h, fill=trough, outline="")
        if self._hi - self._lo < 0.999:
            pad = 1
            self.create_rectangle(
                pad,
                y0 + pad,
                w - pad,
                y0 + thumb_h - pad,
                fill=thumb,
                outline="",
            )

    def _fraction_at(self, y: int) -> float:
        _, thumb_h, h = self._thumb_metrics()
        travel = max(1, h - thumb_h)
        return max(0.0, min(1.0, (y - thumb_h / 2) / travel))

    def _on_down(self, event):
        self._dragging = True
        self._jump(event.y)

    def _on_drag(self, event):
        if self._dragging:
            self._jump(event.y)

    def _on_up(self, _event):
        self._dragging = False
        self._draw()

    def _jump(self, y: int):
        if not self._command:
            return
        frac = self._fraction_at(y)
        self._command("moveto", frac)


def make_scroll_body(
    parent: tk.Misc, theme: dict, *, bg_key: str = "surface"
) -> tuple[tk.Frame, tk.Canvas, tk.Frame]:
    """Vertical scroll area; returns (outer, canvas, inner_frame)."""
    outer = tk.Frame(parent, bg=theme["bg"])
    canvas = tk.Canvas(outer, bg=theme[bg_key], highlightthickness=0, bd=0)
    scroll = ThemedVScrollbar(outer, theme, command=canvas.yview)
    canvas.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    inner = tk.Frame(canvas, bg=theme[bg_key], padx=16, pady=14)
    window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _sync_scroll(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _sync_width(event):
        canvas.itemconfigure(window_id, width=max(1, event.width))

    inner.bind("<Configure>", _sync_scroll)
    canvas.bind("<Configure>", _sync_width)

    def _wheel(event):
        if event.delta:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def bind_wheel(widget=None):
        target = widget or inner
        target.bind("<MouseWheel>", _wheel)
        for child in target.winfo_children():
            bind_wheel(child)

    canvas.bind("<MouseWheel>", _wheel)
    outer.bind_wheel = bind_wheel  # type: ignore[attr-defined]
    return outer, canvas, inner
