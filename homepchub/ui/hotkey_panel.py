"""Global hotkey settings — click a row and press the combo (keyboard capture)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from homepchub.core import hotkeys as hotkey_engine
from homepchub.core.config import load_config
from homepchub.i18n import t
from homepchub.ui.layout import ThemedVScrollbar, size_window
from homepchub.ui.theme import FONTS, apply_ttk, get_theme
from homepchub.ui.winchrome import dress_window


def _device_label(device: dict, socket: int | None = None) -> str:
    name = device.get("alias") or device.get("host") or device.get("id")
    if socket is None:
        return str(name)
    sockets = device.get("sockets") or []
    sock = next((s for s in sockets if int(s.get("index", -1)) == int(socket)), None)
    sock_name = (sock or {}).get("alias") or t("status.socket_n", n=int(socket) + 1)
    return f"{name} · {sock_name}"


def open_hotkey_panel(parent: tk.Misc, theme_mode: str) -> None:
    theme = get_theme(theme_mode)
    win = tk.Toplevel(parent)
    win.title(t("hotkey.title"))
    win.configure(bg=theme["bg"])
    win.transient(parent)
    win.grab_set()
    dress_window(win, theme, dark=theme_mode == "dark")
    size_window(win, 520, 520, min_width=420, min_height=360)

    style = ttk.Style(win)
    apply_ttk(style, theme)

    root = tk.Frame(win, bg=theme["bg"], padx=16, pady=14)
    root.pack(fill="both", expand=True)

    tk.Label(
        root,
        text=t("hotkey.title"),
        bg=theme["bg"],
        fg=theme["text"],
        font=FONTS["title"],
        anchor="w",
    ).pack(fill="x")
    tk.Label(
        root,
        text=t("hotkey.blurb"),
        bg=theme["bg"],
        fg=theme["text_muted"],
        font=FONTS["subtitle"],
        anchor="w",
        wraplength=460,
        justify="left",
    ).pack(fill="x", pady=(4, 12))

    if not hotkey_engine.available():
        tk.Label(
            root,
            text=t("hotkey.missing"),
            bg=theme["bg"],
            fg=theme["text"],
            font=FONTS["ui"],
            wraplength=460,
            justify="left",
        ).pack(fill="x")
        ttk.Button(root, text=t("hotkey.close"), command=win.destroy).pack(
            anchor="e", pady=(16, 0)
        )
        return

    hk = hotkey_engine.get_hotkeys()
    values: dict[str, tk.StringVar] = {
        "flyout": tk.StringVar(value=hk["flyout"]),
        "settings": tk.StringVar(value=hk["settings"]),
    }
    active_capture: dict[str, object | None] = {"row": None}

    list_wrap = tk.Frame(root, bg=theme["bg"])
    list_wrap.pack(fill="both", expand=True)
    canvas = tk.Canvas(list_wrap, bg=theme["bg"], highlightthickness=0, bd=0)
    scroll = ThemedVScrollbar(list_wrap, theme, command=canvas.yview)
    body = tk.Frame(canvas, bg=theme["bg"])
    body.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    win_id = canvas.create_window((0, 0), window=body, anchor="nw")

    def _stretch(event):
        canvas.itemconfigure(win_id, width=event.width)

    canvas.bind("<Configure>", _stretch)
    canvas.configure(yscrollcommand=scroll.set)
    canvas.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    def _btn_text(var: tk.StringVar) -> str:
        cur = (var.get() or "").strip()
        return cur if cur else t("hotkey.empty")

    def _add_row(parent: tk.Misc, label: str, var: tk.StringVar, row: int):
        tk.Label(
            parent,
            text=label,
            bg=theme["bg"],
            fg=theme["text"],
            font=FONTS["ui"],
            anchor="w",
        ).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)

        btn = ttk.Button(parent, text=_btn_text(var), style="Ghost.TButton", width=22)
        btn.grid(row=row, column=1, sticky="ew", pady=5)

        def refresh_btn():
            if active_capture["row"] is btn:
                btn.configure(text=t("hotkey.listening"))
            else:
                btn.configure(text=_btn_text(var))

        def on_got(combo: str | None):
            active_capture["row"] = None
            if combo is not None:
                var.set(combo)
            refresh_btn()

        def start_capture():
            if active_capture["row"] is not None:
                hotkey_engine.cancel_capture()
                active_capture["row"] = None
            active_capture["row"] = btn
            refresh_btn()

            def done(combo: str | None, og=on_got):
                win.after(0, lambda c=combo: og(c))

            if not hotkey_engine.begin_capture(done):
                on_got(None)
                messagebox.showerror(t("hotkey.title"), t("hotkey.missing"), parent=win)

        btn.configure(command=start_capture)

        def clear():
            if active_capture["row"] is btn:
                hotkey_engine.cancel_capture()
                active_capture["row"] = None
            var.set("")
            refresh_btn()

        ttk.Button(
            parent, text=t("hotkey.clear"), style="Ghost.TButton", command=clear, width=8
        ).grid(row=row, column=2, sticky="e", padx=(8, 0), pady=5)
        parent.columnconfigure(1, weight=1)

    # App actions
    section = tk.Label(
        body,
        text=t("hotkey.section_app"),
        bg=theme["bg"],
        fg=theme["text_muted"],
        font=FONTS["ui_bold"],
        anchor="w",
    )
    section.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
    _add_row(body, t("hotkey.flyout"), values["flyout"], 1)
    _add_row(body, t("hotkey.settings"), values["settings"], 2)

    # Devices
    tk.Label(
        body,
        text=t("hotkey.section_devices"),
        bg=theme["bg"],
        fg=theme["text_muted"],
        font=FONTS["ui_bold"],
        anchor="w",
    ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(14, 4))

    targets = dict(hk["targets"])
    row_i = 4
    devices = load_config().get("devices") or []
    if not devices:
        tk.Label(
            body,
            text=t("hotkey.no_devices"),
            bg=theme["bg"],
            fg=theme["text_muted"],
            font=FONTS["subtitle"],
            anchor="w",
        ).grid(row=row_i, column=0, columnspan=3, sticky="w")
        row_i += 1

    for device in devices:
        did = device.get("id")
        if not did:
            continue
        sockets = device.get("sockets") or []
        if sockets and (
            device.get("kind") == "strip" or int(device.get("socket_count") or 0) > 1
        ):
            for s in sockets:
                idx = int(s.get("index"))
                key = hotkey_engine.target_key(did, idx)
                var = tk.StringVar(value=targets.get(key, ""))
                values[key] = var
                _add_row(body, _device_label(device, idx), var, row_i)
                row_i += 1
        else:
            key = hotkey_engine.target_key(did)
            var = tk.StringVar(value=targets.get(key, ""))
            values[key] = var
            _add_row(body, _device_label(device), var, row_i)
            row_i += 1

    foot = tk.Frame(root, bg=theme["bg"])
    foot.pack(fill="x", pady=(12, 0))

    def on_close():
        hotkey_engine.cancel_capture()
        win.destroy()

    def on_save():
        hotkey_engine.cancel_capture()
        targets_out = {
            k: v.get().strip()
            for k, v in values.items()
            if k not in ("flyout", "settings") and v.get().strip()
        }
        # drop stale targets for removed devices (already only current rows)
        hotkey_engine.set_hotkeys(
            flyout=values["flyout"].get(),
            settings=values["settings"].get(),
            targets=targets_out,
        )
        win.destroy()

    ttk.Button(foot, text=t("hotkey.cancel"), style="Ghost.TButton", command=on_close).pack(
        side="right"
    )
    ttk.Button(foot, text=t("hotkey.save"), style="Accent.TButton", command=on_save).pack(
        side="right", padx=(0, 8)
    )

    win.protocol("WM_DELETE_WINDOW", on_close)
