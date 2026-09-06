"""Windows multi-monitor helpers (Home Hub-style identify + bbox)."""

from __future__ import annotations

import sys
import tkinter as tk

IDENTIFY_POPUP_MS = 1800


def list_monitors() -> list[tuple[int, int, int, int]]:
    """Return (left, top, right, bottom) for each display, or [] if unavailable."""
    if sys.platform != "win32":
        return []
    try:
        import ctypes
        from ctypes import wintypes

        monitors: list[tuple[int, int, int, int]] = []
        MonitorEnumProc = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.POINTER(wintypes.RECT),
            ctypes.c_double,
        )

        def callback(_hmonitor, _hdc, rect, _data):
            r = rect.contents
            monitors.append((r.left, r.top, r.right, r.bottom))
            return 1

        ctypes.windll.user32.EnumDisplayMonitors(0, 0, MonitorEnumProc(callback), 0)
        return monitors
    except Exception:
        return []


def show_monitor_identifiers(root: tk.Misc) -> None:
    """Flash a large number on each monitor (like Windows Display Identify)."""
    for i, (left, top, right, bottom) in enumerate(list_monitors()):
        size = 160
        cx = left + (right - left) // 2
        cy = top + (bottom - top) // 2
        popup = tk.Toplevel(root)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg="#1a1a1a")
        popup.geometry(f"{size}x{size}+{cx - size // 2}+{cy - size // 2}")
        tk.Label(
            popup,
            text=str(i + 1),
            font=("Segoe UI", 72, "bold"),
            fg="white",
            bg="#1a1a1a",
        ).pack(expand=True, fill="both")
        popup.after(IDENTIFY_POPUP_MS, popup.destroy)
