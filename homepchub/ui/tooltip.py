"""Small (i) hint icon with hover tooltip."""

from __future__ import annotations

import tkinter as tk


class ToolTip:
    def __init__(self, widget: tk.Misc, text: str, *, delay_ms: int = 350):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after = None
        self._tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None):
        self._cancel()
        self._after = self.widget.after(self.delay_ms, self._show)

    def _cancel(self):
        if self._after is not None:
            self.widget.after_cancel(self._after)
            self._after = None

    def _hide(self, _event=None):
        self._cancel()
        if self._tip is not None:
            try:
                self._tip.destroy()
            except tk.TclError:
                pass
            self._tip = None

    def _show(self):
        if self._tip is not None or not self.text:
            return
        tip = tk.Toplevel(self.widget)
        tip.wm_overrideredirect(True)
        tip.attributes("-topmost", True)
        try:
            tip.attributes("-alpha", 0.96)
        except tk.TclError:
            pass

        frame = tk.Frame(tip, bg="#1a2030", padx=1, pady=1)
        frame.pack()
        lbl = tk.Label(
            frame,
            text=self.text,
            justify="left",
            background="#2a3344",
            foreground="#e8ecf2",
            relief="flat",
            font=("Bahnschrift", 9),
            padx=10,
            pady=8,
            wraplength=280,
        )
        lbl.pack()

        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        tip.wm_geometry(f"+{x}+{y}")
        self._tip = tip


def attach_info_icon(
    parent: tk.Misc,
    text: str,
    *,
    bg: str,
    fg: str = "#8b95a8",
    accent: str = "#e8a45c",
) -> tk.Canvas:
    """Pack a tiny (i) circle; hover shows `text`."""
    size = 16
    canvas = tk.Canvas(
        parent,
        width=size,
        height=size,
        bg=bg,
        highlightthickness=0,
        bd=0,
        cursor="question_arrow",
    )
    canvas.create_oval(1, 1, size - 2, size - 2, outline=accent, width=1.5)
    canvas.create_text(
        size / 2,
        size / 2,
        text="i",
        fill=accent,
        font=("Bahnschrift", 8, "bold"),
    )
    ToolTip(canvas, text)
    return canvas


def labeled_row(
    parent: tk.Misc,
    title: str,
    help_text: str,
    *,
    bg: str,
    fg: str,
    muted: str,
    accent: str,
    font_title,
    font_meta=None,
    meta: str | None = None,
) -> tk.Frame:
    """Title + info icon (+ optional meta line)."""
    wrap = tk.Frame(parent, bg=bg)
    title_row = tk.Frame(wrap, bg=bg)
    title_row.pack(anchor="w", fill="x")
    tk.Label(
        title_row,
        text=title,
        bg=bg,
        fg=fg,
        font=font_title,
        anchor="w",
    ).pack(side="left")
    icon = attach_info_icon(title_row, help_text, bg=bg, fg=muted, accent=accent)
    icon.pack(side="left", padx=(6, 0))
    if meta:
        tk.Label(
            wrap,
            text=meta,
            bg=bg,
            fg=muted,
            font=font_meta,
            anchor="w",
        ).pack(anchor="w")
    return wrap
