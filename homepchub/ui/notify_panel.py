"""Notification automation rules - scene-like steps + app filter."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from homepchub.core import notifications as notify
from homepchub.core import presets as bulb_presets
from homepchub.core.presets import store as preset_store
from homepchub.i18n import t
from homepchub.ui.layout import size_window
from homepchub.ui.theme import FONTS, apply_ttk, get_theme
from homepchub.ui.winchrome import dress_window


def _action_label(step: dict) -> str:
    action = step.get("action")
    if action == notify.ACTION_WAIT:
        return t("scene.wait_label", ms=int(step.get("ms") or 0))
    if action == notify.ACTION_SET_HSV:
        return t(
            "notify.action.set_hsv_label",
            h=step.get("hue"),
            s=step.get("saturation"),
            b=step.get("brightness"),
        )
    if action == notify.ACTION_RESTORE:
        return t("notify.action.restore")
    if action == notify.ACTION_APPLY_MODE:
        return f"{t('preset.action.apply_mode')}: {bulb_presets.preset_label(step.get('preset_id'))}"
    return {
        notify.ACTION_ON: t("preset.action.on"),
        notify.ACTION_OFF: t("preset.action.off"),
        notify.ACTION_TOGGLE: t("preset.action.toggle"),
    }.get(action, action or "?")


def open_notify_panel(parent: tk.Misc, theme_mode: str) -> None:
    theme = get_theme(theme_mode)
    win = tk.Toplevel(parent)
    win.title(t("notify.title"))
    win.configure(bg=theme["bg"])
    win.transient(parent)
    win.grab_set()
    dress_window(win, theme, dark=theme_mode == "dark")
    size_window(win, 820, 620, min_width=700, min_height=500)

    style = ttk.Style(win)
    apply_ttk(style, theme)

    root = tk.Frame(win, bg=theme["bg"], padx=18, pady=16)
    root.pack(fill="both", expand=True)
    root.columnconfigure(1, weight=1)
    root.rowconfigure(3, weight=1)

    tk.Label(
        root,
        text=t("notify.title"),
        bg=theme["bg"],
        fg=theme["text"],
        font=FONTS["title"],
        anchor="w",
    ).grid(row=0, column=0, columnspan=2, sticky="ew")
    tk.Label(
        root,
        text=t("notify.blurb"),
        bg=theme["bg"],
        fg=theme["text_muted"],
        font=FONTS["subtitle"],
        anchor="w",
        wraplength=760,
        justify="left",
    ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 8))

    settings = notify.get_settings()
    enabled_var = tk.BooleanVar(value=settings["enabled"])

    top = tk.Frame(root, bg=theme["bg"])
    top.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
    ttk.Checkbutton(
        top,
        text=t("notify.enabled"),
        variable=enabled_var,
    ).pack(side="left")
    if not notify.available():
        tk.Label(
            top,
            text=t("notify.missing"),
            bg=theme["bg"],
            fg=theme["text_muted"],
            font=FONTS["meta"],
            anchor="w",
        ).pack(side="left", padx=(12, 0))

    left = tk.Frame(root, bg=theme["surface"], padx=10, pady=10)
    left.grid(row=3, column=0, sticky="nsw", padx=(0, 12))
    tk.Label(
        left,
        text=t("notify.rules"),
        bg=theme["surface"],
        fg=theme["text_muted"],
        font=FONTS["ui_bold"],
        anchor="w",
    ).pack(fill="x")
    rule_list = tk.Listbox(
        left,
        bg=theme["surface_2"],
        fg=theme["text"],
        selectbackground=theme["accent"],
        selectforeground=theme["accent_text"],
        font=FONTS["ui"],
        height=18,
        width=22,
        activestyle="none",
        borderwidth=0,
        highlightthickness=0,
        exportselection=False,
    )
    rule_list.pack(fill="y", pady=(8, 0))

    form = tk.Frame(root, bg=theme["surface"], padx=14, pady=12)
    form.grid(row=3, column=1, sticky="nsew")
    form.columnconfigure(0, weight=1)

    name_var = tk.StringVar()
    apps_var = tk.StringVar()
    rule_enabled_var = tk.BooleanVar(value=True)

    ttk.Label(form, text=t("notify.rule_name"), style="Surface.TLabel").grid(
        row=0, column=0, sticky="w"
    )
    ttk.Entry(form, textvariable=name_var, font=FONTS["ui"]).grid(
        row=1, column=0, sticky="ew", pady=(4, 8)
    )

    ttk.Label(form, text=t("notify.apps"), style="Surface.TLabel").grid(
        row=2, column=0, sticky="w"
    )
    tk.Label(
        form,
        text=t("notify.apps_blurb"),
        bg=theme["surface"],
        fg=theme["text_muted"],
        font=FONTS["meta"],
        anchor="w",
        wraplength=480,
        justify="left",
    ).grid(row=3, column=0, sticky="ew")
    apps_combo = ttk.Combobox(
        form,
        textvariable=apps_var,
        values=list(notify.APP_SUGGESTIONS),
        font=FONTS["ui"],
    )
    apps_combo.grid(row=4, column=0, sticky="ew", pady=(4, 8))

    ttk.Checkbutton(
        form, text=t("notify.rule_enabled"), variable=rule_enabled_var
    ).grid(row=5, column=0, sticky="w", pady=(0, 8))

    ttk.Label(form, text=t("notify.steps"), style="Surface.TLabel").grid(
        row=6, column=0, sticky="w"
    )
    tk.Label(
        form,
        text=t("notify.steps_blurb"),
        bg=theme["surface"],
        fg=theme["text_muted"],
        font=FONTS["meta"],
        anchor="w",
        wraplength=480,
        justify="left",
    ).grid(row=7, column=0, sticky="ew")

    steps_list = tk.Listbox(
        form,
        bg=theme["surface_2"],
        fg=theme["text"],
        selectbackground=theme["accent"],
        selectforeground=theme["accent_text"],
        font=FONTS["meta"],
        height=7,
        activestyle="none",
        borderwidth=0,
        highlightthickness=0,
        exportselection=False,
    )
    steps_list.grid(row=8, column=0, sticky="ew", pady=(6, 0))

    add_row = tk.Frame(form, bg=theme["surface"])
    add_row.grid(row=9, column=0, sticky="ew", pady=(10, 0))
    add_row.columnconfigure(0, weight=2)
    add_row.columnconfigure(1, weight=2)

    wait_target = {
        "kind": "wait",
        "label": t("scene.wait_target"),
        "key": "__wait__",
        "device_id": None,
        "socket": None,
    }
    targets = [wait_target] + preset_store.iter_action_targets()
    target_by_label = {tgt["label"]: tgt for tgt in targets}
    target_var = tk.StringVar(
        value=targets[1]["label"] if len(targets) > 1 else wait_target["label"]
    )
    target_combo = ttk.Combobox(
        add_row,
        textvariable=target_var,
        values=[tgt["label"] for tgt in targets],
        state="readonly",
        width=24,
    )
    target_combo.grid(row=0, column=0, sticky="ew", padx=(0, 8))

    action_var = tk.StringVar()
    action_combo = ttk.Combobox(add_row, textvariable=action_var, state="readonly", width=16)
    action_combo.grid(row=0, column=1, sticky="ew", padx=(0, 8))

    mode_ids = bulb_presets.list_preset_ids()
    mode_labels = [bulb_presets.preset_label(pid) for pid in mode_ids]
    mode_by_label = dict(zip(mode_labels, mode_ids))
    mode_var = tk.StringVar(value=mode_labels[0] if mode_labels else "")
    mode_combo = ttk.Combobox(
        add_row, textvariable=mode_var, values=mode_labels, state="readonly", width=14
    )

    wait_ms_var = tk.StringVar(value="400")
    wait_wrap = tk.Frame(add_row, bg=theme["surface"])
    ttk.Label(wait_wrap, text=t("scene.wait_ms"), style="Surface.TLabel").pack(
        side="left", padx=(0, 6)
    )
    ttk.Entry(wait_wrap, textvariable=wait_ms_var, width=8, font=FONTS["ui"]).pack(
        side="left"
    )

    hsv_wrap = tk.Frame(add_row, bg=theme["surface"])
    hue_var = tk.StringVar(value="0")
    sat_var = tk.StringVar(value="100")
    bri_var = tk.StringVar(value="100")
    ttk.Label(hsv_wrap, text="H", style="Surface.TLabel").pack(side="left")
    ttk.Entry(hsv_wrap, textvariable=hue_var, width=4, font=FONTS["ui"]).pack(
        side="left", padx=(2, 6)
    )
    ttk.Label(hsv_wrap, text="S", style="Surface.TLabel").pack(side="left")
    ttk.Entry(hsv_wrap, textvariable=sat_var, width=4, font=FONTS["ui"]).pack(
        side="left", padx=(2, 6)
    )
    ttk.Label(hsv_wrap, text="V", style="Surface.TLabel").pack(side="left")
    ttk.Entry(hsv_wrap, textvariable=bri_var, width=4, font=FONTS["ui"]).pack(
        side="left", padx=(2, 0)
    )

    selected: dict[str, str | None] = {"id": None}
    draft_steps: list[dict] = []
    ids: list[str] = []

    def sync_action_choices(_e=None) -> None:
        tgt = target_by_label.get(target_var.get())
        mode_combo.grid_remove()
        wait_wrap.grid_remove()
        hsv_wrap.grid_remove()
        if not tgt:
            action_combo.configure(values=[], state="disabled")
            return
        if tgt["kind"] == "wait":
            action_combo.grid_remove()
            wait_wrap.grid(row=0, column=1, columnspan=2, sticky="w")
            return
        action_combo.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        action_combo.configure(state="readonly")
        if tgt["kind"] == "bulb":
            choices = [
                t("notify.action.set_hsv"),
                t("notify.action.restore"),
                t("preset.action.apply_mode"),
                t("preset.action.on"),
                t("preset.action.off"),
                t("preset.action.toggle"),
            ]
            keys = [
                notify.ACTION_SET_HSV,
                notify.ACTION_RESTORE,
                notify.ACTION_APPLY_MODE,
                notify.ACTION_ON,
                notify.ACTION_OFF,
                notify.ACTION_TOGGLE,
            ]
        else:
            choices = [
                t("preset.action.on"),
                t("preset.action.off"),
                t("preset.action.toggle"),
            ]
            keys = [notify.ACTION_ON, notify.ACTION_OFF, notify.ACTION_TOGGLE]
        action_combo.configure(values=choices)
        action_combo._keys = keys  # type: ignore[attr-defined]
        action_var.set(choices[0])
        sync_extra()

    def sync_extra(_e=None) -> None:
        tgt = target_by_label.get(target_var.get())
        mode_combo.grid_remove()
        wait_wrap.grid_remove()
        hsv_wrap.grid_remove()
        if not tgt or tgt["kind"] == "wait":
            return
        keys = getattr(action_combo, "_keys", [])
        choices = list(action_combo.cget("values") or [])
        try:
            action = keys[choices.index(action_var.get())]
        except (ValueError, IndexError):
            return
        if action == notify.ACTION_APPLY_MODE and mode_labels:
            mode_combo.grid(row=0, column=2, sticky="ew")
            mode_combo.configure(state="readonly")
        elif action == notify.ACTION_SET_HSV:
            hsv_wrap.grid(row=0, column=2, sticky="w")

    target_combo.bind("<<ComboboxSelected>>", sync_action_choices)
    action_combo.bind("<<ComboboxSelected>>", sync_extra)
    sync_action_choices()

    def refresh_steps() -> None:
        steps_list.delete(0, "end")
        label_by_key = {tgt["key"]: tgt["label"] for tgt in targets}
        for step in draft_steps:
            if step.get("action") == notify.ACTION_WAIT:
                steps_list.insert("end", _action_label(step))
                continue
            sock = step.get("socket")
            key = f"{step['device_id']}:{'' if sock is None else sock}"
            dev = label_by_key.get(key, step["device_id"])
            steps_list.insert("end", f"{dev} → {_action_label(step)}")

    def on_add_step() -> None:
        tgt = target_by_label.get(target_var.get())
        if not tgt:
            return
        if tgt["kind"] == "wait":
            try:
                ms = int((wait_ms_var.get() or "").strip())
            except ValueError:
                messagebox.showerror(t("notify.title"), t("scene.wait_invalid"), parent=win)
                return
            draft_steps.append({"action": notify.ACTION_WAIT, "ms": max(0, ms)})
            refresh_steps()
            return
        keys = getattr(action_combo, "_keys", [])
        choices = list(action_combo.cget("values") or [])
        try:
            action = keys[choices.index(action_var.get())]
        except (ValueError, IndexError):
            return
        step: dict = {
            "device_id": tgt["device_id"],
            "socket": tgt["socket"],
            "action": action,
        }
        if action == notify.ACTION_APPLY_MODE:
            pid = mode_by_label.get(mode_var.get())
            if not pid:
                return
            step["preset_id"] = pid
            step["socket"] = None
        elif action == notify.ACTION_SET_HSV:
            try:
                step.update(
                    {
                        "socket": None,
                        "hue": max(0, min(360, int(hue_var.get()))),
                        "saturation": max(0, min(100, int(sat_var.get()))),
                        "brightness": max(1, min(100, int(bri_var.get()))),
                    }
                )
            except ValueError:
                messagebox.showerror(t("notify.title"), t("notify.hsv_invalid"), parent=win)
                return
        elif action == notify.ACTION_RESTORE:
            step["socket"] = None
        draft_steps.append(step)
        refresh_steps()

    def on_remove_step() -> None:
        sel = steps_list.curselection()
        if not sel:
            return
        del draft_steps[sel[0]]
        refresh_steps()

    btns = tk.Frame(form, bg=theme["surface"])
    btns.grid(row=10, column=0, sticky="w", pady=(8, 0))
    ttk.Button(btns, text=t("scene.add_step"), command=on_add_step).pack(side="left")
    ttk.Button(
        btns, text=t("scene.remove_step"), style="Ghost.TButton", command=on_remove_step
    ).pack(side="left", padx=(6, 0))

    def refresh_list(select_id: str | None = None) -> None:
        nonlocal ids
        rules = notify.get_settings()["rules"]
        ids = [r["id"] for r in rules]
        rule_list.delete(0, "end")
        for r in rules:
            mark = "" if r.get("enabled", True) else " (off)"
            rule_list.insert("end", f"{r['label']}{mark}")
        if select_id and select_id in ids:
            idx = ids.index(select_id)
            rule_list.selection_set(idx)
            load_selected()
        elif ids:
            rule_list.selection_set(0)
            load_selected()
        else:
            selected["id"] = None
            name_var.set("")
            apps_var.set("")
            draft_steps.clear()
            refresh_steps()

    def load_selected(_e=None) -> None:
        nonlocal draft_steps
        sel = rule_list.curselection()
        if not sel:
            return
        rid = ids[sel[0]]
        rule = next((r for r in notify.get_settings()["rules"] if r["id"] == rid), None)
        if not rule:
            return
        selected["id"] = rid
        name_var.set(rule["label"])
        apps_var.set(", ".join(rule.get("apps") or []))
        rule_enabled_var.set(bool(rule.get("enabled", True)))
        draft_steps = list(rule.get("steps") or [])
        refresh_steps()

    rule_list.bind("<<ListboxSelect>>", load_selected)

    def on_save_rule() -> None:
        label = name_var.get().strip()
        if not label:
            messagebox.showerror(t("notify.title"), t("notify.need_name"), parent=win)
            return
        apps = [a.strip() for a in apps_var.get().split(",") if a.strip()]
        try:
            item = notify.upsert_rule(
                rule_id=selected.get("id"),
                label=label,
                apps=apps,
                steps=list(draft_steps),
                enabled=rule_enabled_var.get(),
            )
        except Exception as exc:
            messagebox.showerror(t("notify.title"), str(exc), parent=win)
            return
        # persist global enabled too
        notify.set_settings(enabled=enabled_var.get(), rules=notify.get_settings()["rules"])
        refresh_list(item["id"])
        messagebox.showinfo(t("notify.title"), t("notify.saved"), parent=win)

    def on_new() -> None:
        selected["id"] = None
        rule_list.selection_clear(0, "end")
        name_var.set(t("notify.new_name"))
        apps_var.set("")
        rule_enabled_var.set(True)
        draft_steps.clear()
        refresh_steps()

    def on_delete() -> None:
        rid = selected.get("id")
        if not rid:
            return
        if not messagebox.askyesno(t("notify.title"), t("notify.delete_confirm"), parent=win):
            return
        notify.delete_rule(rid)
        notify.set_settings(enabled=enabled_var.get(), rules=notify.get_settings()["rules"])
        refresh_list()

    def on_test() -> None:
        rid = selected.get("id")
        if not rid:
            messagebox.showinfo(t("notify.title"), t("notify.save_first"), parent=win)
            return
        rule = next((r for r in notify.get_settings()["rules"] if r["id"] == rid), None)
        if not rule:
            return

        def go():
            try:
                notify.apply_rule(rule)
            except Exception:
                pass

        threading.Thread(target=go, daemon=True).start()

    def on_close() -> None:
        notify.set_settings(enabled=enabled_var.get(), rules=notify.get_settings()["rules"])
        win.destroy()

    foot = tk.Frame(root, bg=theme["bg"])
    foot.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
    ttk.Button(foot, text=t("notify.new"), style="Ghost.TButton", command=on_new).pack(
        side="left"
    )
    ttk.Button(
        foot, text=t("notify.delete"), style="Ghost.TButton", command=on_delete
    ).pack(side="left", padx=(6, 0))
    ttk.Button(foot, text=t("notify.test"), style="Ghost.TButton", command=on_test).pack(
        side="left", padx=(6, 0)
    )
    ttk.Button(foot, text=t("notify.close"), style="Ghost.TButton", command=on_close).pack(
        side="right"
    )
    ttk.Button(
        foot, text=t("notify.save"), style="Accent.TButton", command=on_save_rule
    ).pack(side="right", padx=(0, 8))

    win.protocol("WM_DELETE_WINDOW", on_close)
    refresh_list()
