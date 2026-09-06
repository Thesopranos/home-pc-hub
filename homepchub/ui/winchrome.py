"""Match native Windows title bar (caption / border) to app theme."""

from __future__ import annotations

import ctypes
import sys
import tkinter as tk
from typing import Any

# DWM window attributes (Windows 10 1903+ / Windows 11)
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_BORDER_COLOR = 34
_DWMWA_CAPTION_COLOR = 35
_DWMWA_TEXT_COLOR = 36


def _hex_to_colorref(hex_color: str) -> int:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return r | (g << 8) | (b << 16)


def _toplevel_hwnd(widget: tk.Misc) -> int | None:
    if sys.platform != "win32":
        return None
    try:
        widget.update_idletasks()
        hwnd = int(widget.winfo_id())
        user32 = ctypes.windll.user32
        # Tk's winfo_id is often the client child; walk to the frame HWND.
        parent = user32.GetParent(hwnd)
        while parent:
            style = user32.GetWindowLongW(parent, -16)  # GWL_STYLE
            # WS_CAPTION | WS_SYSMENU → real chrome window
            if style & 0x00C00000:
                hwnd = parent
                break
            next_parent = user32.GetParent(parent)
            if not next_parent:
                hwnd = parent
                break
            parent = next_parent
        return hwnd or None
    except Exception:
        return None


def apply_window_chrome(widget: tk.Misc, theme: dict[str, Any], *, dark: bool) -> None:
    """Tint caption bar, border, and immersive dark mode for a Tk top-level."""
    if sys.platform != "win32":
        return
    hwnd = _toplevel_hwnd(widget)
    if not hwnd:
        return
    try:
        dwm = ctypes.windll.dwmapi
        value = ctypes.c_int(1 if dark else 0)
        dwm.DwmSetWindowAttribute(
            hwnd,
            _DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
        caption = ctypes.c_int(_hex_to_colorref(theme["bg"]))
        border = ctypes.c_int(_hex_to_colorref(theme.get("border", theme["bg"])))
        text = ctypes.c_int(_hex_to_colorref(theme["text"]))
        for attr, color in (
            (_DWMWA_CAPTION_COLOR, caption),
            (_DWMWA_BORDER_COLOR, border),
            (_DWMWA_TEXT_COLOR, text),
        ):
            dwm.DwmSetWindowAttribute(
                hwnd, attr, ctypes.byref(color), ctypes.sizeof(color)
            )
    except Exception:
        pass


def schedule_window_chrome(
    widget: tk.Misc, theme: dict[str, Any], *, dark: bool
) -> None:
    """Apply after the window is mapped (needed for fresh Toplevels)."""
    widget._chrome_theme = theme  # type: ignore[attr-defined]
    widget._chrome_dark = dark  # type: ignore[attr-defined]

    def _go(_event=None):
        t = getattr(widget, "_chrome_theme", theme)
        d = bool(getattr(widget, "_chrome_dark", dark))
        apply_window_chrome(widget, t, dark=d)

    try:
        widget.after_idle(_go)
        if not getattr(widget, "_chrome_map_bound", False):
            widget._chrome_map_bound = True  # type: ignore[attr-defined]
            widget.bind("<Map>", _go, add="+")
    except Exception:
        apply_window_chrome(widget, theme, dark=dark)


def dress_window(widget: tk.Misc, theme: dict[str, Any], *, dark: bool) -> None:
    """Brand icon (no Tk feather) + caption colors matching theme."""
    from homepchub.assets import apply_window_icons

    if not getattr(widget, "_brand_icons_set", False):
        apply_window_icons(widget)
        widget._brand_icons_set = True  # type: ignore[attr-defined]
    schedule_window_chrome(widget, theme, dark=dark)
