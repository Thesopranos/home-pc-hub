"""Readonly ambient-mode Combobox for bulb panel and tray flyout."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable

from homepchub.core import presets as bulb_presets
from homepchub.i18n import t
from homepchub.i18n.labels import ui_help
from homepchub.ui.tooltip import attach_info_icon


def add_preset_select(
    parent: tk.Misc,
    *,
    host: str,
    device_id: str | None,
    active_preset: str | None,
    after: Callable,
    status_set: Callable[[str], None],
    theme: dict,
    width: int = 22,
) -> ttk.Combobox | None:
    preset_ids = bulb_presets.list_preset_ids()
    if not preset_ids:
        return None

    labels = [bulb_presets.preset_label(pid) for pid in preset_ids]
    by_label = dict(zip(labels, preset_ids))
    placeholder = t("preset.choose")
    values = [placeholder, *labels]

    initial = placeholder
    if active_preset and active_preset in bulb_presets.REGISTRY:
        initial = bulb_presets.preset_label(active_preset)

    row = tk.Frame(parent, bg=theme["surface"])
    var = tk.StringVar(value=initial)
    combo = ttk.Combobox(
        row,
        textvariable=var,
        values=values,
        state="readonly",
        width=width,
    )
    combo.set(initial)
    combo.pack(side="left", fill="x", expand=True)
    attach_info_icon(
        row,
        ui_help("preset_modes"),
        bg=theme["surface"],
        fg=theme["text_muted"],
        accent=theme["accent"],
    ).pack(side="left", padx=(8, 0))

    def on_pick(_e=None):
        label = var.get()
        preset_id = by_label.get(label)
        if not preset_id:
            return
        status_set(t("preset.applying"))

        def go():
            try:
                bulb_presets.apply_preset(host, preset_id, device_id=device_id)
                msg = t("preset.applied", name=label)
            except Exception as exc:
                msg = t("status.error", error=exc)

            def done():
                try:
                    if not parent.winfo_exists():
                        return
                except tk.TclError:
                    return
                status_set(msg)
                combo.set(label)

            after(0, done)

        threading.Thread(target=go, daemon=True).start()

    combo.bind("<<ComboboxSelected>>", on_pick)
    return row
