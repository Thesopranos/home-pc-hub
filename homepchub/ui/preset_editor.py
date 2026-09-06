"""Editor for ambient modes, Kelvin/brightness, and linked device actions."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from homepchub.core import presets as bulb_presets
from homepchub.core.presets import store as preset_store
from homepchub.core.presets.base import reload_custom_presets
from homepchub.i18n import t
from homepchub.ui.layout import size_window
from homepchub.ui.theme import FONTS, apply_ttk, get_theme
from homepchub.ui.winchrome import dress_window


def _action_label(action: str) -> str:
    return {
        preset_store.ACTION_APPLY_MODE: t("preset.action.apply_mode"),
        preset_store.ACTION_ON: t("preset.action.on"),
        preset_store.ACTION_OFF: t("preset.action.off"),
        preset_store.ACTION_TOGGLE: t("preset.action.toggle"),
    }.get(action, action)


def open_preset_editor(parent: tk.Misc, theme_mode: str) -> None:
    theme = get_theme(theme_mode)
    win = tk.Toplevel(parent)
    win.title(t("preset.editor.title"))
    win.configure(bg=theme["bg"])
    win.transient(parent)
    win.grab_set()
    dress_window(win, theme, dark=theme_mode == "dark")
    size_window(win, 640, 560, min_width=520, min_height=460)

    style = ttk.Style(win)
    apply_ttk(style, theme)

    root = tk.Frame(win, bg=theme["bg"], padx=16, pady=14)
    root.pack(fill="both", expand=True)

    tk.Label(
        root,
        text=t("preset.editor.title"),
        bg=theme["bg"],
        fg=theme["text"],
        font=FONTS["title"],
        anchor="w",
    ).pack(fill="x")
    tk.Label(
        root,
        text=t("preset.editor.blurb"),
        bg=theme["bg"],
        fg=theme["text_muted"],
        font=FONTS["subtitle"],
        wraplength=600,
        justify="left",
        anchor="w",
    ).pack(fill="x", pady=(4, 10))

    body = tk.Frame(root, bg=theme["bg"])
    body.pack(fill="both", expand=True)
    body.columnconfigure(1, weight=1)
    body.rowconfigure(0, weight=1)

    list_wrap = tk.Frame(body, bg=theme["surface"], padx=8, pady=8)
    list_wrap.grid(row=0, column=0, sticky="nsw", padx=(0, 10))
    mode_list = tk.Listbox(
        list_wrap,
        bg=theme["surface_2"],
        fg=theme["text"],
        selectbackground=theme["accent"],
        selectforeground=theme["accent_text"],
        font=FONTS["ui"],
        width=18,
        height=18,
        activestyle="none",
        borderwidth=0,
        highlightthickness=0,
    )
    mode_list.pack(fill="both", expand=True)

    form = tk.Frame(body, bg=theme["surface"], padx=12, pady=12)
    form.grid(row=0, column=1, sticky="nsew")
    form.columnconfigure(1, weight=1)

    name_var = tk.StringVar()
    kelvin_var = tk.StringVar()
    bright_var = tk.StringVar()
    selected: dict[str, str | None] = {"id": None}
    draft_actions: list[dict] = []

    ttk.Label(form, text=t("preset.editor.name"), style="Surface.TLabel").grid(
        row=0, column=0, sticky="w"
    )
    name_entry = ttk.Entry(form, textvariable=name_var, width=28)
    name_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0))

    ttk.Label(form, text=t("preset.editor.kelvin"), style="Surface.TLabel").grid(
        row=1, column=0, sticky="w", pady=(8, 0)
    )
    kelvin_entry = ttk.Entry(form, textvariable=kelvin_var, width=10)
    kelvin_entry.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(8, 0))

    ttk.Label(form, text=t("preset.editor.brightness"), style="Surface.TLabel").grid(
        row=2, column=0, sticky="w", pady=(8, 0)
    )
    bright_entry = ttk.Entry(form, textvariable=bright_var, width=10)
    bright_entry.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=(8, 0))

    # --- Linked actions ---
    ttk.Label(form, text=t("preset.editor.actions"), style="Surface.TLabel").grid(
        row=3, column=0, columnspan=2, sticky="w", pady=(14, 4)
    )
    tk.Label(
        form,
        text=t("preset.editor.actions_blurb"),
        bg=theme["surface"],
        fg=theme["text_muted"],
        font=FONTS["meta"],
        wraplength=360,
        justify="left",
        anchor="w",
    ).grid(row=4, column=0, columnspan=2, sticky="ew")

    actions_list = tk.Listbox(
        form,
        bg=theme["surface_2"],
        fg=theme["text"],
        selectbackground=theme["accent"],
        selectforeground=theme["accent_text"],
        font=FONTS["meta"],
        height=5,
        activestyle="none",
        borderwidth=0,
        highlightthickness=0,
    )
    actions_list.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(6, 0))

    add_row = tk.Frame(form, bg=theme["surface"])
    add_row.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(8, 0))
    add_row.columnconfigure(0, weight=1)

    targets = preset_store.iter_action_targets()
    target_by_label = {tgt["label"]: tgt for tgt in targets}
    target_var = tk.StringVar(
        value=targets[0]["label"] if targets else t("preset.editor.no_devices")
    )
    target_combo = ttk.Combobox(
        add_row,
        textvariable=target_var,
        values=[tgt["label"] for tgt in targets],
        state="readonly" if targets else "disabled",
        width=28,
    )
    target_combo.grid(row=0, column=0, sticky="ew")

    action_var = tk.StringVar()
    action_combo = ttk.Combobox(
        add_row, textvariable=action_var, state="readonly", width=16
    )
    action_combo.grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def sync_action_choices(_e=None) -> None:
        tgt = target_by_label.get(target_var.get())
        if not tgt:
            action_combo.configure(values=[])
            action_var.set("")
            return
        if tgt["kind"] == "bulb":
            choices = [
                t("preset.action.apply_mode"),
                t("preset.action.on"),
                t("preset.action.off"),
                t("preset.action.toggle"),
            ]
            keys = [
                preset_store.ACTION_APPLY_MODE,
                preset_store.ACTION_ON,
                preset_store.ACTION_OFF,
                preset_store.ACTION_TOGGLE,
            ]
        else:
            choices = [
                t("preset.action.on"),
                t("preset.action.off"),
                t("preset.action.toggle"),
            ]
            keys = [
                preset_store.ACTION_ON,
                preset_store.ACTION_OFF,
                preset_store.ACTION_TOGGLE,
            ]
        action_combo.configure(values=choices)
        action_combo._keys = keys  # type: ignore[attr-defined]
        if choices:
            action_var.set(choices[0])

    target_combo.bind("<<ComboboxSelected>>", sync_action_choices)
    sync_action_choices()

    def refresh_actions_view() -> None:
        actions_list.delete(0, "end")
        label_by_key = {tgt["key"]: tgt["label"] for tgt in targets}
        for step in draft_actions:
            key = f"{step['device_id']}:{'' if step.get('socket') is None else step['socket']}"
            dev = label_by_key.get(key, step["device_id"])
            actions_list.insert("end", f"{dev} → {_action_label(step['action'])}")

    def on_add_action() -> None:
        tgt = target_by_label.get(target_var.get())
        if not tgt:
            return
        keys = getattr(action_combo, "_keys", [])
        choices = list(action_combo.cget("values") or [])
        try:
            idx = choices.index(action_var.get())
            action = keys[idx]
        except (ValueError, IndexError):
            return
        # Ampul olmayan hedeflerde apply_mode yok
        if action == preset_store.ACTION_APPLY_MODE and tgt["kind"] != "bulb":
            return
        draft_actions.append(
            {
                "device_id": tgt["device_id"],
                "socket": tgt["socket"],
                "action": action,
            }
        )
        refresh_actions_view()

    def on_remove_action() -> None:
        sel = actions_list.curselection()
        if not sel:
            return
        del draft_actions[sel[0]]
        refresh_actions_view()

    act_btns = tk.Frame(form, bg=theme["surface"])
    act_btns.grid(row=7, column=0, columnspan=2, sticky="w", pady=(6, 0))
    ttk.Button(
        act_btns, text=t("preset.editor.add_action"), style="TButton", command=on_add_action
    ).pack(side="left")
    ttk.Button(
        act_btns,
        text=t("preset.editor.remove_action"),
        style="Ghost.TButton",
        command=on_remove_action,
    ).pack(side="left", padx=(6, 0))

    ids: list[str] = []

    def refresh_list(select_id: str | None = None) -> None:
        nonlocal ids
        reload_custom_presets()
        # All modes can carry linked actions; static/custom also edit light recipe
        ids = bulb_presets.list_preset_ids()
        mode_list.delete(0, "end")
        for pid in ids:
            mode_list.insert("end", bulb_presets.preset_label(pid))
        if select_id and select_id in ids:
            idx = ids.index(select_id)
            mode_list.selection_clear(0, "end")
            mode_list.selection_set(idx)
            mode_list.activate(idx)
            load_selected()
        elif ids:
            mode_list.selection_set(0)
            load_selected()

    def set_light_fields_enabled(enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        kelvin_entry.configure(state=state)
        bright_entry.configure(state=state)

    def load_selected(_e=None) -> None:
        nonlocal draft_actions
        sel = mode_list.curselection()
        if not sel:
            return
        pid = ids[sel[0]]
        selected["id"] = pid
        entry = bulb_presets.REGISTRY.get(pid) or {}
        name_var.set(bulb_presets.preset_label(pid))
        editable = bool(entry.get("editable"))
        if editable:
            kelvin, bright = preset_store.get_static_params(pid)
            kelvin_var.set(str(kelvin))
            bright_var.set(str(bright))
            set_light_fields_enabled(True)
            if entry.get("custom"):
                name_entry.configure(state="normal")
            else:
                name_entry.configure(state="disabled")
        else:
            kelvin_var.set("-")
            bright_var.set("-")
            set_light_fields_enabled(False)
            name_entry.configure(state="disabled")
        draft_actions = preset_store.get_actions(pid)
        refresh_actions_view()

    def parse_fields() -> tuple[int, int]:
        try:
            kelvin = int(kelvin_var.get().strip())
            bright = int(bright_var.get().strip())
        except ValueError as exc:
            raise ValueError(t("preset.editor.invalid")) from exc
        if not (2500 <= kelvin <= 6500 and 1 <= bright <= 100):
            raise ValueError(t("preset.editor.invalid"))
        return kelvin, bright

    def on_save() -> None:
        pid = selected.get("id")
        if not pid:
            return
        entry = bulb_presets.REGISTRY.get(pid) or {}
        try:
            if entry.get("editable"):
                kelvin, bright = parse_fields()
                if entry.get("custom"):
                    preset_store.update_custom(
                        pid, label=name_var.get(), kelvin=kelvin, brightness=bright
                    )
                    reload_custom_presets()
                else:
                    preset_store.set_static_override(
                        pid, kelvin=kelvin, brightness=bright
                    )
            preset_store.set_actions(pid, list(draft_actions))
        except Exception as exc:
            messagebox.showerror(t("preset.editor.title"), str(exc), parent=win)
            return
        refresh_list(pid)
        messagebox.showinfo(t("preset.editor.title"), t("preset.editor.saved"), parent=win)

    def on_new() -> None:
        try:
            kelvin, bright = parse_fields()
        except ValueError:
            kelvin, bright = 3000, 50
        label = (name_var.get() or "").strip() or t("preset.editor.new_name")
        try:
            item = preset_store.add_custom(
                label=label, kelvin=kelvin, brightness=bright
            )
            if draft_actions:
                preset_store.set_actions(item["id"], list(draft_actions))
            reload_custom_presets()
            refresh_list(item["id"])
        except Exception as exc:
            messagebox.showerror(t("preset.editor.title"), str(exc), parent=win)

    def on_delete() -> None:
        pid = selected.get("id")
        if not pid:
            return
        entry = bulb_presets.REGISTRY.get(pid) or {}
        if not entry.get("custom"):
            if entry.get("editable"):
                preset_store.reset_static_override(pid)
            preset_store.set_actions(pid, [])
            draft_actions.clear()
            refresh_list(pid)
            messagebox.showinfo(
                t("preset.editor.title"), t("preset.editor.reset"), parent=win
            )
            return
        if not messagebox.askyesno(
            t("preset.editor.title"), t("preset.editor.delete_confirm"), parent=win
        ):
            return
        preset_store.delete_custom(pid)
        reload_custom_presets()
        selected["id"] = None
        refresh_list()

    def on_reset_new_form() -> None:
        nonlocal draft_actions
        selected["id"] = None
        mode_list.selection_clear(0, "end")
        name_entry.configure(state="normal")
        set_light_fields_enabled(True)
        name_var.set(t("preset.editor.new_name"))
        kelvin_var.set("3000")
        bright_var.set("50")
        draft_actions = []
        refresh_actions_view()

    btns = tk.Frame(root, bg=theme["bg"])
    btns.pack(fill="x", pady=(12, 0))
    ttk.Button(
        btns, text=t("preset.editor.save"), style="Accent.TButton", command=on_save
    ).pack(side="left")
    ttk.Button(
        btns, text=t("preset.editor.add"), style="TButton", command=on_new
    ).pack(side="left", padx=(8, 0))
    ttk.Button(
        btns, text=t("preset.editor.delete"), style="Ghost.TButton", command=on_delete
    ).pack(side="left", padx=(8, 0))
    ttk.Button(
        btns,
        text=t("preset.editor.clear"),
        style="Ghost.TButton",
        command=on_reset_new_form,
    ).pack(side="left", padx=(8, 0))
    ttk.Button(
        btns, text=t("plug.close"), style="Ghost.TButton", command=win.destroy
    ).pack(side="right")

    mode_list.bind("<<ListboxSelect>>", load_selected)
    refresh_list()
