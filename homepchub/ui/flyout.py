"""Compact tray flyout — quick power toggles (Home Hub-style single click)."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk

from homepchub.assets import logo_photo
from homepchub.core.config import get_theme_mode, load_config
from homepchub.core.devices import get_status, set_power
from homepchub.i18n import t
from homepchub.ui.preset_picker import add_preset_select
from homepchub.ui.theme import FONTS, apply_ttk, get_theme
from homepchub.ui.window import ToggleSwitch

_flyout_window = None
_POLL_MS = 4000


def close_flyout() -> None:
    global _flyout_window
    if _flyout_window is not None:
        win = _flyout_window
        _flyout_window = None
        try:
            win.destroy()
        except tk.TclError:
            pass


def _is_bulb(device: dict) -> bool:
    return device.get("kind") == "bulb" or bool(device.get("has_light"))


def _add_preset_select(
    parent: tk.Misc,
    theme: dict,
    device: dict,
    *,
    status_var: tk.StringVar,
) -> None:
    wrap = tk.Frame(parent, bg=theme["surface"])
    wrap.pack(fill="x", pady=(0, 6))
    tk.Label(
        wrap,
        text=t("preset.section"),
        bg=theme["surface"],
        fg=theme["text_muted"],
        font=FONTS["meta"],
        anchor="w",
    ).pack(fill="x", pady=(0, 4))
    combo_row = add_preset_select(
        wrap,
        host=device["host"],
        device_id=device.get("id"),
        active_preset=device.get("active_preset"),
        after=parent.after,
        status_set=status_var.set,
        theme=theme,
        width=24,
    )
    if combo_row is not None:
        combo_row.pack(fill="x")


def open_flyout(root: tk.Tk, *, on_open_full=None) -> None:
    global _flyout_window
    if _flyout_window is not None and _flyout_window.winfo_exists():
        close_flyout()
        return

    mode = get_theme_mode()
    theme = get_theme(mode)
    win = tk.Toplevel(root)
    _flyout_window = win
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.configure(bg=theme.get("border", theme["text_muted"]))

    style = ttk.Style(win)
    apply_ttk(style, theme)

    border = tk.Frame(win, bg=theme.get("border", theme["text_muted"]), padx=1, pady=1)
    border.pack()
    inner = tk.Frame(border, bg=theme["surface"], padx=14, pady=12)
    inner.pack()

    header = tk.Frame(inner, bg=theme["surface"])
    header.pack(fill="x", pady=(0, 10))
    try:
        logo = logo_photo(win, mode, height=28)
        win._flyout_logo = logo  # keep reference
        tk.Label(
            header,
            image=logo,
            bg=theme["surface"],
            anchor="w",
        ).pack(side="left")
    except Exception:
        tk.Label(
            header,
            text="Home Pc Hub",
            bg=theme["surface"],
            fg=theme["text"],
            font=FONTS["ui_bold"],
            anchor="w",
        ).pack(side="left")
    tk.Label(
        header,
        text=t("tray.flyout_hint"),
        bg=theme["surface"],
        fg=theme["text_muted"],
        font=FONTS["meta"],
        anchor="e",
    ).pack(side="right")

    body = tk.Frame(inner, bg=theme["surface"])
    body.pack(fill="both", expand=True)

    status_var = tk.StringVar(value="")
    devices = load_config().get("devices") or []
    rows: list[dict] = []

    if not devices:
        tk.Label(
            body,
            text=t("tray.flyout_empty"),
            bg=theme["surface"],
            fg=theme["text_muted"],
            font=FONTS["subtitle"],
            wraplength=280,
            justify="left",
        ).pack(anchor="w")
    else:
        def _divider():
            tk.Frame(body, bg=theme["border"], height=1).pack(
                fill="x", pady=(8, 6)
            )

        for i, device in enumerate(devices):
            if i > 0:
                _divider()
            kind = device.get("kind") or "other"
            socket_count = int(device.get("socket_count") or 0)
            is_multi = kind == "strip" or socket_count > 0
            name = device.get("alias") or device["host"]
            is_bulb = _is_bulb(device) and not is_multi

            if is_multi:
                tk.Label(
                    body,
                    text=name,
                    bg=theme["surface"],
                    fg=theme["text"],
                    font=FONTS["ui_bold"],
                    anchor="w",
                ).pack(fill="x", pady=(0, 2))
                sockets = device.get("sockets") or [
                    {"index": i, "alias": t("status.socket_n", n=i + 1)}
                    for i in range(socket_count)
                ]
                sock_switches: dict[int, ToggleSwitch] = {}
                for s_i, sock in enumerate(sockets):
                    if s_i > 0:
                        tk.Frame(body, bg=theme["border"], height=1).pack(
                            fill="x", pady=(4, 4)
                        )
                    idx = int(sock["index"])
                    row = tk.Frame(body, bg=theme["surface"])
                    row.pack(fill="x", pady=2)
                    tk.Label(
                        row,
                        text=sock.get("alias") or t("status.socket_n", n=idx + 1),
                        bg=theme["surface"],
                        fg=theme["text"],
                        font=FONTS["ui"],
                        anchor="w",
                    ).pack(side="left")

                    def on_sock(on, host=device["host"], s=idx):
                        def go():
                            try:
                                set_power(host, on, socket=s)
                            except Exception:
                                pass

                        threading.Thread(target=go, daemon=True).start()

                    sw = ToggleSwitch(row, theme, on_toggle=on_sock, state=False)
                    sw._bg = theme["surface"]
                    sw.configure(bg=theme["surface"])
                    sw.pack(side="right")
                    sock_switches[idx] = sw
                rows.append(
                    {
                        "host": device["host"],
                        "multi": True,
                        "socket_switches": sock_switches,
                    }
                )
            else:
                block = tk.Frame(body, bg=theme["surface"])
                block.pack(fill="x", pady=(0 if not is_bulb else 0, 0))
                row = tk.Frame(block, bg=theme["surface"])
                row.pack(fill="x")
                tk.Label(
                    row,
                    text=name,
                    bg=theme["surface"],
                    fg=theme["text"],
                    font=FONTS["ui_bold"] if is_bulb else FONTS["ui"],
                    anchor="w",
                ).pack(side="left", fill="x", expand=True)

                def on_dev(on, host=device["host"]):
                    def go():
                        try:
                            set_power(host, on, socket=None)
                        except Exception:
                            pass

                    threading.Thread(target=go, daemon=True).start()

                sw = ToggleSwitch(row, theme, on_toggle=on_dev, state=False)
                sw._bg = theme["surface"]
                sw.configure(bg=theme["surface"])
                sw.pack(side="right")
                rows.append({"host": device["host"], "multi": False, "switch": sw})

                if is_bulb:
                    _add_preset_select(block, theme, device, status_var=status_var)

    footer = tk.Frame(inner, bg=theme["surface"])
    footer.pack(fill="x", pady=(10, 0))
    tk.Label(
        footer,
        textvariable=status_var,
        bg=theme["surface"],
        fg=theme["text_muted"],
        font=FONTS["meta"],
        anchor="w",
    ).pack(side="left", fill="x", expand=True)

    def open_full():
        close_flyout()
        if on_open_full:
            on_open_full()

    ttk.Button(
        footer, text=t("tray.open_full"), style="Accent.TButton", command=open_full
    ).pack(side="right")

    def refresh_states():
        if _flyout_window is not win or not win.winfo_exists():
            return

        def worker():
            updates = []
            for row in rows:
                try:
                    data = get_status(row["host"])
                    updates.append((row, data))
                except Exception:
                    updates.append((row, None))

            def apply():
                if not win.winfo_exists():
                    return
                for row, data in updates:
                    if data is None:
                        continue
                    if row["multi"]:
                        for s in data.get("sockets") or []:
                            sw = row["socket_switches"].get(int(s["index"]))
                            if sw:
                                sw.set_state(bool(s["is_on"]))
                    else:
                        row["switch"].set_state(bool(data.get("is_on")))
                win.after(_POLL_MS, refresh_states)

            win.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    win.update_idletasks()
    width, height = win.winfo_width(), win.winfo_height()
    x = root.winfo_screenwidth() - width - 12
    y = root.winfo_screenheight() - height - 56
    win.geometry(f"+{x}+{y}")

    def maybe_close(_event=None):
        win.after(80, lambda: win.focus_get() is None and close_flyout())

    win.bind("<FocusOut>", maybe_close)
    win.focus_force()
    refresh_states()
