"""Editor for named scenes (multi-device one-tap automations)."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from homepchub.core import presets as bulb_presets
from homepchub.core import scenes as scene_store
from homepchub.core.presets import store as preset_store
from homepchub.i18n import t
from homepchub.ui.layout import size_window
from homepchub.ui.theme import FONTS, apply_ttk, get_theme
from homepchub.ui.winchrome import dress_window


def _action_label(action: str, preset_id: str | None = None, ms: int | None = None) -> str:
    if action == scene_store.ACTION_WAIT:
        return t("scene.wait_label", ms=int(ms or 0))
    if action == scene_store.ACTION_APPLY_MODE:
        mode = bulb_presets.preset_label(preset_id) if preset_id else "?"
        return f"{t('preset.action.apply_mode')}: {mode}"
    return {
        scene_store.ACTION_ON: t("preset.action.on"),
        scene_store.ACTION_OFF: t("preset.action.off"),
        scene_store.ACTION_TOGGLE: t("preset.action.toggle"),
    }.get(action, action)


def open_scene_panel(parent: tk.Misc, theme_mode: str) -> None:
    theme = get_theme(theme_mode)
    win = tk.Toplevel(parent)
    win.title(t("scene.title"))
    win.configure(bg=theme["bg"])
    win.transient(parent)
    win.grab_set()
    dress_window(win, theme, dark=theme_mode == "dark")
    size_window(win, 780, 580, min_width=680, min_height=480)

    style = ttk.Style(win)
    apply_ttk(style, theme)

    root = tk.Frame(win, bg=theme["bg"], padx=18, pady=16)
    root.pack(fill="both", expand=True)
    root.columnconfigure(1, weight=1)
    root.rowconfigure(2, weight=1)

    tk.Label(
        root,
        text=t("scene.title"),
        bg=theme["bg"],
        fg=theme["text"],
        font=FONTS["title"],
        anchor="w",
    ).grid(row=0, column=0, columnspan=2, sticky="ew")
    tk.Label(
        root,
        text=t("scene.blurb"),
        bg=theme["bg"],
        fg=theme["text_muted"],
        font=FONTS["subtitle"],
        anchor="w",
        wraplength=720,
        justify="left",
    ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 12))

    # Left: scene list
    left = tk.Frame(root, bg=theme["surface"], padx=10, pady=10)
    left.grid(row=2, column=0, sticky="nsw", padx=(0, 12))
    tk.Label(
        left,
        text=t("scene.list"),
        bg=theme["surface"],
        fg=theme["text_muted"],
        font=FONTS["ui_bold"],
        anchor="w",
    ).pack(fill="x")
    scene_list = tk.Listbox(
        left,
        bg=theme["surface_2"],
        fg=theme["text"],
        selectbackground=theme["accent"],
        selectforeground=theme["accent_text"],
        font=FONTS["ui"],
        height=16,
        width=22,
        activestyle="none",
        borderwidth=0,
        highlightthickness=0,
    )
    scene_list.pack(fill="y", pady=(8, 0))

    # Right: editor
    form = tk.Frame(root, bg=theme["surface"], padx=14, pady=12)
    form.grid(row=2, column=1, sticky="nsew")
    form.columnconfigure(0, weight=1)

    name_var = tk.StringVar()
    ttk.Label(form, text=t("scene.name"), style="Surface.TLabel").grid(
        row=0, column=0, sticky="w"
    )
    name_entry = ttk.Entry(form, textvariable=name_var, font=FONTS["ui"])
    name_entry.grid(row=1, column=0, sticky="ew", pady=(4, 10))

    ttk.Label(form, text=t("scene.steps"), style="Surface.TLabel").grid(
        row=2, column=0, sticky="w"
    )
    tk.Label(
        form,
        text=t("scene.steps_blurb"),
        bg=theme["surface"],
        fg=theme["text_muted"],
        font=FONTS["meta"],
        anchor="w",
        wraplength=480,
        justify="left",
    ).grid(row=3, column=0, sticky="ew", pady=(2, 0))

    steps_list = tk.Listbox(
        form,
        bg=theme["surface_2"],
        fg=theme["text"],
        selectbackground=theme["accent"],
        selectforeground=theme["accent_text"],
        font=FONTS["meta"],
        height=8,
        activestyle="none",
        borderwidth=0,
        highlightthickness=0,
        cursor="hand2",
    )
    steps_list.grid(row=4, column=0, sticky="ew", pady=(6, 0))
    tk.Label(
        form,
        text=t("scene.edit_hint"),
        bg=theme["surface"],
        fg=theme["text_muted"],
        font=FONTS["meta"],
        anchor="w",
    ).grid(row=5, column=0, sticky="ew", pady=(4, 0))

    add_row = tk.Frame(form, bg=theme["surface"])
    add_row.grid(row=6, column=0, sticky="ew", pady=(8, 0))
    add_row.columnconfigure(0, weight=3)
    add_row.columnconfigure(1, weight=2)
    add_row.columnconfigure(2, weight=2)

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
        width=28,
    )
    target_combo.grid(row=0, column=0, sticky="ew", padx=(0, 10))

    action_var = tk.StringVar()
    action_combo = ttk.Combobox(
        add_row, textvariable=action_var, state="readonly", width=16
    )
    action_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10))

    mode_ids = bulb_presets.list_preset_ids()
    mode_labels = [bulb_presets.preset_label(pid) for pid in mode_ids]
    mode_by_label = dict(zip(mode_labels, mode_ids))
    mode_var = tk.StringVar(value=mode_labels[0] if mode_labels else "")
    mode_combo = ttk.Combobox(
        add_row,
        textvariable=mode_var,
        values=mode_labels,
        state="readonly" if mode_labels else "disabled",
        width=16,
    )

    wait_ms_var = tk.StringVar(value="500")
    wait_wrap = tk.Frame(add_row, bg=theme["surface"])
    ttk.Label(wait_wrap, text=t("scene.wait_ms"), style="Surface.TLabel").pack(
        side="left", padx=(0, 6)
    )
    wait_entry = ttk.Entry(wait_wrap, textvariable=wait_ms_var, width=10, font=FONTS["ui"])
    wait_entry.pack(side="left")

    selected: dict[str, str | None] = {"id": None}
    draft_steps: list[dict] = []
    ids: list[str] = []

    def sync_action_choices(_e=None) -> None:
        tgt = target_by_label.get(target_var.get())
        if not tgt:
            action_combo.configure(values=[], state="disabled")
            action_var.set("")
            mode_combo.grid_remove()
            wait_wrap.grid_remove()
            return
        if tgt["kind"] == "wait":
            action_combo.grid_remove()
            mode_combo.grid_remove()
            action_combo._keys = []  # type: ignore[attr-defined]
            wait_wrap.grid(row=0, column=1, columnspan=2, sticky="w")
            return
        wait_wrap.grid_remove()
        action_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        action_combo.configure(state="readonly")
        if tgt["kind"] == "bulb":
            choices = [
                t("preset.action.apply_mode"),
                t("preset.action.on"),
                t("preset.action.off"),
                t("preset.action.toggle"),
            ]
            keys = [
                scene_store.ACTION_APPLY_MODE,
                scene_store.ACTION_ON,
                scene_store.ACTION_OFF,
                scene_store.ACTION_TOGGLE,
            ]
        else:
            choices = [
                t("preset.action.on"),
                t("preset.action.off"),
                t("preset.action.toggle"),
            ]
            keys = [
                scene_store.ACTION_ON,
                scene_store.ACTION_OFF,
                scene_store.ACTION_TOGGLE,
            ]
        action_combo.configure(values=choices)
        action_combo._keys = keys  # type: ignore[attr-defined]
        if choices:
            action_var.set(choices[0])
        sync_mode_visibility()

    def sync_mode_visibility(_e=None) -> None:
        tgt = target_by_label.get(target_var.get())
        if tgt is None or tgt.get("kind") == "wait":
            mode_combo.grid_remove()
            return
        is_bulb = tgt.get("kind") == "bulb" and bool(mode_labels)
        if not is_bulb:
            mode_combo.grid_remove()
            return
        mode_combo.grid(row=0, column=2, sticky="ew")
        keys = getattr(action_combo, "_keys", [])
        choices = list(action_combo.cget("values") or [])
        try:
            idx = choices.index(action_var.get())
            action = keys[idx]
        except (ValueError, IndexError):
            action = None
        if action == scene_store.ACTION_APPLY_MODE:
            mode_combo.configure(state="readonly")
        else:
            mode_combo.configure(state="disabled")

    target_combo.bind("<<ComboboxSelected>>", sync_action_choices)
    action_combo.bind("<<ComboboxSelected>>", sync_mode_visibility)
    sync_action_choices()

    editing = {"index": None, "loading": False}

    def refresh_steps_view(select_index: int | None = None) -> None:
        steps_list.delete(0, "end")
        label_by_key = {tgt["key"]: tgt["label"] for tgt in targets}
        for step in draft_steps:
            if step.get("action") == scene_store.ACTION_WAIT:
                steps_list.insert(
                    "end",
                    _action_label(scene_store.ACTION_WAIT, ms=step.get("ms")),
                )
                continue
            sock = step.get("socket")
            key = f"{step['device_id']}:{'' if sock is None else sock}"
            dev = label_by_key.get(key, step["device_id"])
            steps_list.insert(
                "end",
                f"{dev} → {_action_label(step['action'], step.get('preset_id'))}",
            )
        if select_index is not None and 0 <= select_index < len(draft_steps):
            steps_list.selection_clear(0, "end")
            steps_list.selection_set(select_index)
            steps_list.activate(select_index)
            steps_list.see(select_index)
            editing["index"] = select_index
        elif editing["index"] is not None and editing["index"] >= len(draft_steps):
            editing["index"] = None

    def _step_same(a: dict, b: dict) -> bool:
        if a.get("action") == scene_store.ACTION_WAIT or b.get("action") == scene_store.ACTION_WAIT:
            return (
                a.get("action") == scene_store.ACTION_WAIT
                and b.get("action") == scene_store.ACTION_WAIT
                and a.get("ms") == b.get("ms")
            )
        return (
            a.get("device_id") == b.get("device_id")
            and a.get("socket") == b.get("socket")
            and a.get("action") == b.get("action")
            and a.get("preset_id") == b.get("preset_id")
        )

    def _consecutive_conflict(step: dict, at: int) -> bool:
        """True if step at index `at` would sit next to an identical non-wait neighbor."""
        if step.get("action") == scene_store.ACTION_WAIT:
            if at > 0 and _step_same(draft_steps[at - 1], step):
                return True
            if at + 1 < len(draft_steps) and _step_same(draft_steps[at + 1], step):
                return True
            return False
        prev = None
        for j in range(at - 1, -1, -1):
            if draft_steps[j].get("action") == scene_store.ACTION_WAIT:
                continue
            prev = draft_steps[j]
            break
        if prev is not None and _step_same(prev, step):
            return True
        nxt = None
        for j in range(at + 1, len(draft_steps)):
            if draft_steps[j].get("action") == scene_store.ACTION_WAIT:
                continue
            nxt = draft_steps[j]
            break
        if nxt is not None and _step_same(nxt, step):
            return True
        return False

    def _build_step_from_form() -> dict | None:
        tgt = target_by_label.get(target_var.get())
        if not tgt:
            return None
        if tgt["kind"] == "wait":
            try:
                ms = int((wait_ms_var.get() or "").strip())
            except ValueError:
                messagebox.showerror(t("scene.title"), t("scene.wait_invalid"), parent=win)
                return None
            if ms < 0 or ms > 600_000:
                messagebox.showerror(t("scene.title"), t("scene.wait_invalid"), parent=win)
                return None
            return {"action": scene_store.ACTION_WAIT, "ms": ms}
        keys = getattr(action_combo, "_keys", [])
        choices = list(action_combo.cget("values") or [])
        try:
            idx = choices.index(action_var.get())
            action = keys[idx]
        except (ValueError, IndexError):
            return None
        step = {
            "device_id": tgt["device_id"],
            "socket": tgt["socket"],
            "action": action,
        }
        if action == scene_store.ACTION_APPLY_MODE:
            if tgt["kind"] != "bulb":
                return None
            pid = mode_by_label.get(mode_var.get())
            if not pid:
                return None
            step["preset_id"] = pid
        return step

    def load_step_into_form(index: int) -> None:
        if index < 0 or index >= len(draft_steps):
            editing["index"] = None
            return
        step = draft_steps[index]
        editing["loading"] = True
        editing["index"] = index
        try:
            if step.get("action") == scene_store.ACTION_WAIT:
                target_var.set(wait_target["label"])
                sync_action_choices()
                wait_ms_var.set(str(int(step.get("ms") or 0)))
            else:
                sock = step.get("socket")
                key = f"{step['device_id']}:{'' if sock is None else sock}"
                label = None
                for tgt in targets:
                    if tgt.get("key") == key:
                        label = tgt["label"]
                        break
                if label is None:
                    editing["loading"] = False
                    return
                target_var.set(label)
                sync_action_choices()
                keys = getattr(action_combo, "_keys", [])
                choices = list(action_combo.cget("values") or [])
                action = step.get("action")
                if action in keys:
                    action_var.set(choices[keys.index(action)])
                sync_mode_visibility()
                if action == scene_store.ACTION_APPLY_MODE:
                    pid = step.get("preset_id")
                    for lbl, mid in mode_by_label.items():
                        if mid == pid:
                            mode_var.set(lbl)
                            break
            steps_list.selection_clear(0, "end")
            steps_list.selection_set(index)
            steps_list.activate(index)
        finally:
            editing["loading"] = False

    drag = {"index": None, "moved": False}

    def _steps_drag_start(event):
        idx = steps_list.nearest(event.y)
        drag["moved"] = False
        if 0 <= idx < len(draft_steps):
            drag["index"] = idx
            steps_list.selection_clear(0, "end")
            steps_list.selection_set(idx)
            steps_list.activate(idx)
        else:
            drag["index"] = None

    def _steps_drag_motion(event):
        from_i = drag["index"]
        if from_i is None:
            return
        to_i = steps_list.nearest(event.y)
        if to_i < 0 or to_i >= len(draft_steps) or to_i == from_i:
            return
        draft_steps.insert(to_i, draft_steps.pop(from_i))
        drag["index"] = to_i
        drag["moved"] = True
        refresh_steps_view(to_i)

    def _steps_drag_end(_event=None):
        idx = drag["index"]
        drag["index"] = None
        drag["moved"] = False
        if idx is not None and 0 <= idx < len(draft_steps):
            load_step_into_form(idx)

    steps_list.bind("<ButtonPress-1>", _steps_drag_start)
    steps_list.bind("<B1-Motion>", _steps_drag_motion)
    steps_list.bind("<ButtonRelease-1>", _steps_drag_end)

    def on_add_step() -> None:
        step = _build_step_from_form()
        if not step:
            return
        at = len(draft_steps)
        # temporarily append for neighbor check against previous only
        if step.get("action") == scene_store.ACTION_WAIT:
            if (
                draft_steps
                and draft_steps[-1].get("action") == scene_store.ACTION_WAIT
                and draft_steps[-1].get("ms") == step.get("ms")
            ):
                messagebox.showinfo(t("scene.title"), t("scene.duplicate_step"), parent=win)
                return
        else:
            prev = None
            for existing in reversed(draft_steps):
                if existing.get("action") == scene_store.ACTION_WAIT:
                    continue
                prev = existing
                break
            if prev is not None and _step_same(prev, step):
                messagebox.showinfo(t("scene.title"), t("scene.duplicate_step"), parent=win)
                return
        draft_steps.append(step)
        editing["index"] = None
        refresh_steps_view()
        steps_list.selection_clear(0, "end")

    def on_update_step() -> None:
        idx = editing.get("index")
        if idx is None or idx < 0 or idx >= len(draft_steps):
            messagebox.showinfo(t("scene.title"), t("scene.edit_hint"), parent=win)
            return
        step = _build_step_from_form()
        if not step:
            return
        old = draft_steps[idx]
        draft_steps[idx] = step
        if _consecutive_conflict(step, idx):
            draft_steps[idx] = old
            messagebox.showinfo(t("scene.title"), t("scene.duplicate_step"), parent=win)
            return
        refresh_steps_view(idx)
        load_step_into_form(idx)

    def on_remove_step() -> None:
        sel = steps_list.curselection()
        idx = sel[0] if sel else editing.get("index")
        if idx is None or idx < 0 or idx >= len(draft_steps):
            return
        del draft_steps[idx]
        editing["index"] = None
        refresh_steps_view()
        steps_list.selection_clear(0, "end")

    act_btns = tk.Frame(form, bg=theme["surface"])
    act_btns.grid(row=7, column=0, sticky="w", pady=(6, 0))
    ttk.Button(
        act_btns, text=t("scene.add_step"), style="TButton", command=on_add_step
    ).pack(side="left")
    ttk.Button(
        act_btns,
        text=t("scene.update_step"),
        style="Ghost.TButton",
        command=on_update_step,
    ).pack(side="left", padx=(6, 0))
    ttk.Button(
        act_btns,
        text=t("scene.remove_step"),
        style="Ghost.TButton",
        command=on_remove_step,
    ).pack(side="left", padx=(6, 0))

    def refresh_list(select_id: str | None = None) -> None:
        nonlocal ids
        scenes = scene_store.list_scenes()
        ids = [s["id"] for s in scenes]
        scene_list.delete(0, "end")
        for s in scenes:
            scene_list.insert("end", s["label"])
        if select_id and select_id in ids:
            idx = ids.index(select_id)
            scene_list.selection_clear(0, "end")
            scene_list.selection_set(idx)
            scene_list.activate(idx)
            load_selected()
        elif ids:
            scene_list.selection_set(0)
            load_selected()
        else:
            selected["id"] = None
            name_var.set("")
            draft_steps.clear()
            refresh_steps_view()

    def load_selected(_e=None) -> None:
        nonlocal draft_steps
        sel = scene_list.curselection()
        if not sel:
            return
        sid = ids[sel[0]]
        scene = scene_store.get_scene(sid)
        if not scene:
            return
        selected["id"] = sid
        name_var.set(scene["label"])
        draft_steps = list(scene["steps"])
        editing["index"] = None
        refresh_steps_view()
        if draft_steps:
            load_step_into_form(0)

    scene_list.bind("<<ListboxSelect>>", load_selected)

    def on_save() -> None:
        label = name_var.get().strip()
        if not label:
            messagebox.showerror(t("scene.title"), t("scene.need_name"), parent=win)
            return
        try:
            item = scene_store.upsert_scene(
                scene_id=selected.get("id"),
                label=label,
                steps=list(draft_steps),
            )
        except Exception as exc:
            messagebox.showerror(t("scene.title"), str(exc), parent=win)
            return
        refresh_list(item["id"])
        messagebox.showinfo(t("scene.title"), t("scene.saved"), parent=win)

    def on_new() -> None:
        selected["id"] = None
        scene_list.selection_clear(0, "end")
        name_var.set(t("scene.new_name"))
        draft_steps.clear()
        refresh_steps_view()
        name_entry.focus_set()

    def on_delete() -> None:
        sid = selected.get("id")
        if not sid:
            return
        if not messagebox.askyesno(t("scene.title"), t("scene.delete_confirm"), parent=win):
            return
        scene_store.delete_scene(sid)
        refresh_list()

    def on_apply() -> None:
        sid = selected.get("id")
        if not sid:
            messagebox.showinfo(t("scene.title"), t("scene.save_first"), parent=win)
            return

        def go():
            try:
                scene_store.apply_scene(sid)
            except Exception:
                pass

        threading.Thread(target=go, daemon=True).start()

    foot = tk.Frame(root, bg=theme["bg"])
    foot.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
    ttk.Button(foot, text=t("scene.new"), style="Ghost.TButton", command=on_new).pack(
        side="left"
    )
    ttk.Button(
        foot, text=t("scene.delete"), style="Ghost.TButton", command=on_delete
    ).pack(side="left", padx=(6, 0))
    ttk.Button(
        foot, text=t("scene.apply"), style="Ghost.TButton", command=on_apply
    ).pack(side="left", padx=(6, 0))
    ttk.Button(foot, text=t("scene.close"), style="Ghost.TButton", command=win.destroy).pack(
        side="right"
    )
    ttk.Button(foot, text=t("scene.save"), style="Accent.TButton", command=on_save).pack(
        side="right", padx=(0, 8)
    )

    refresh_list()
