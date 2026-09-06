"""Schedule editor — timed rules and on/off loops are separate tabs."""

from __future__ import annotations

from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

from homepchub.core.config import delete_schedule, get_schedules, upsert_schedule
from homepchub.i18n import t
from homepchub.ui.theme import FONTS, apply_ttk, get_theme
from homepchub.ui.layout import size_window
from homepchub.ui.winchrome import dress_window

WEEKDAY_KEYS = (
    "sched.mon",
    "sched.tue",
    "sched.wed",
    "sched.thu",
    "sched.fri",
    "sched.sat",
    "sched.sun",
)

TIMED_KINDS = (
    ("once", "sched.kind.once"),
    ("daily", "sched.kind.daily"),
    ("weekly", "sched.kind.weekly"),
    ("monthly", "sched.kind.monthly"),
    ("yearly", "sched.kind.yearly"),
)

ACTIONS = (
    ("on", "sched.action_on"),
    ("off", "sched.action_off"),
    ("toggle", "sched.action_toggle"),
)


def _kind_label(kind: str) -> str:
    for k, key in TIMED_KINDS:
        if k == kind:
            return t(key)
    if kind == "loop":
        return t("sched.kind.loop")
    return kind


def _action_label(action: str) -> str:
    for k, key in ACTIONS:
        if k == action:
            return t(key)
    return t("sched.action_on")


def _summarize_timed(rule: dict) -> str:
    en = t("sched.on") if rule.get("enabled", True) else t("sched.off_flag")
    kind = rule.get("kind") or "daily"
    bits = [
        f"[{en}]",
        _kind_label(kind),
        rule.get("time") or "—",
        _action_label(rule.get("action") or "on"),
    ]
    if kind == "once":
        bits.insert(2, rule.get("date") or "—")
    elif kind == "weekly":
        days = rule.get("weekdays") or []
        bits.insert(2, ",".join(str(int(d) + 1) for d in days) or "—")
    elif kind == "monthly":
        bits.insert(2, f"D{rule.get('day_of_month') or '—'}")
    elif kind == "yearly":
        bits.insert(2, f"{rule.get('month') or '—'}/{rule.get('day') or '—'}")
    return " · ".join(str(b) for b in bits)


def _summarize_loop(rule: dict) -> str:
    en = t("sched.on") if rule.get("enabled", True) else t("sched.off_flag")
    return (
        f"[{en}] {rule.get('on_minutes', 0)} {t('sched.min')} "
        f"{t('sched.loop_on_phase')} / "
        f"{rule.get('off_minutes', 0)} {t('sched.min')} "
        f"{t('sched.loop_off_phase')}"
    )


def _sync_device(device: dict, socket: int | None) -> None:
    if socket is None:
        device["schedules"] = get_schedules(device["id"], None)
        return
    for s in device.get("sockets") or []:
        if int(s["index"]) == int(socket):
            s["schedules"] = get_schedules(device["id"], socket)
            break


def open_schedule_panel(
    parent: tk.Misc,
    device: dict,
    theme_mode: str,
    *,
    socket: int | None = None,
) -> None:
    theme = get_theme(theme_mode)
    win = tk.Toplevel(parent)
    base = device.get("alias") or device["host"]
    if socket is not None:
        sock_name = t("status.socket_n", n=socket + 1)
        for s in device.get("sockets") or []:
            if int(s["index"]) == socket:
                sock_name = s.get("alias") or sock_name
                break
        title = f"{base} — {sock_name}"
    else:
        title = base
    win.title(t("sched.title", name=title))
    win.configure(bg=theme["bg"])
    win.resizable(True, True)
    win.transient(parent)
    win.grab_set()
    dress_window(win, theme, dark=theme_mode == "dark")
    size_window(win, 500, 560, min_width=420, min_height=440)

    style = ttk.Style(win)
    apply_ttk(style, theme)

    root = tk.Frame(win, bg=theme["bg"], padx=16, pady=14)
    root.pack(fill="both", expand=True)

    tk.Label(
        root,
        text=title,
        bg=theme["bg"],
        fg=theme["text"],
        font=FONTS["title"],
        anchor="w",
    ).pack(fill="x")

    footer = tk.Frame(root, bg=theme["bg"])
    footer.pack(side="bottom", fill="x", pady=(12, 0))
    ttk.Button(
        footer, text=t("plug.close"), style="Ghost.TButton", command=win.destroy
    ).pack(side="right")

    # Custom tabs — ttk.Notebook draws a harsh system border on Windows
    tabs_bar = tk.Frame(root, bg=theme["bg"])
    tabs_bar.pack(fill="x", pady=(12, 0))
    body_wrap = tk.Frame(
        root,
        bg=theme["border"],
        highlightthickness=0,
        bd=0,
    )
    body_wrap.pack(fill="both", expand=True)
    body_inner = tk.Frame(body_wrap, bg=theme["bg"], padx=1, pady=1)
    body_inner.pack(fill="both", expand=True)

    timed_tab = tk.Frame(body_inner, bg=theme["bg"], padx=8, pady=8)
    loop_tab = tk.Frame(body_inner, bg=theme["bg"], padx=8, pady=8)
    timed_tab.columnconfigure(0, weight=1)
    timed_tab.rowconfigure(1, weight=1)
    loop_tab.columnconfigure(0, weight=1)
    loop_tab.rowconfigure(1, weight=1)

    tab_btns: dict[str, tk.Label] = {}

    def show_tab(name: str) -> None:
        if name == "timed":
            loop_tab.pack_forget()
            timed_tab.pack(fill="both", expand=True)
        else:
            timed_tab.pack_forget()
            loop_tab.pack(fill="both", expand=True)
        for key, lbl in tab_btns.items():
            active = key == name
            lbl.configure(
                bg=theme["bg"] if active else theme["surface_2"],
                fg=theme["text"] if active else theme["text_muted"],
                highlightbackground=theme["border"],
                highlightthickness=1 if active else 0,
            )

    def make_tab(key: str, text: str):
        lbl = tk.Label(
            tabs_bar,
            text=text,
            bg=theme["surface_2"],
            fg=theme["text_muted"],
            font=FONTS["button"],
            padx=14,
            pady=8,
            cursor="hand2",
            highlightthickness=0,
            highlightbackground=theme["border"],
        )
        lbl.pack(side="left", padx=(0, 4))
        lbl.bind("<Button-1>", lambda _e, k=key: show_tab(k))
        tab_btns[key] = lbl

    make_tab("timed", t("sched.tab_timed"))
    make_tab("loop", t("sched.tab_loop"))
    show_tab("timed")

    all_rules: list[dict] = []

    # --- Timed tab ---
    tk.Label(
        timed_tab,
        text=t("sched.timed_blurb"),
        bg=theme["bg"],
        fg=theme["text_muted"],
        font=FONTS["subtitle"],
        wraplength=460,
        justify="left",
        anchor="w",
    ).grid(row=0, column=0, sticky="ew", pady=(0, 8))

    timed_list_wrap = tk.Frame(timed_tab, bg=theme["surface"], padx=8, pady=8)
    timed_list_wrap.grid(row=1, column=0, sticky="nsew")
    timed_list = tk.Listbox(
        timed_list_wrap,
        bg=theme["surface_2"],
        fg=theme["text"],
        selectbackground=theme["accent"],
        selectforeground=theme["accent_text"],
        font=FONTS["ui"],
        height=4,
        activestyle="none",
        borderwidth=0,
        highlightthickness=0,
    )
    timed_list.pack(fill="both", expand=True)
    timed_rules: list[dict] = []

    timed_form = tk.Frame(timed_tab, bg=theme["surface"], padx=10, pady=10)
    timed_form.grid(row=2, column=0, sticky="ew", pady=(8, 0))
    timed_form.columnconfigure(0, minsize=130)
    timed_form.columnconfigure(1, weight=1)

    kind_var = tk.StringVar(value=t("sched.kind.daily"))
    kind_map = {t(key): k for k, key in TIMED_KINDS}
    action_var = tk.StringVar(value=t("sched.action_on"))
    action_map = {t(key): k for k, key in ACTIONS}
    time_var = tk.StringVar(value="08:00")
    date_var = tk.StringVar(value="")
    day_var = tk.StringVar(value="1")
    month_var = tk.StringVar(value="1")
    timed_enabled = tk.BooleanVar(value=True)
    weekday_vars = [tk.BooleanVar(value=False) for _ in range(7)]
    timed_edit: dict[str, str | None] = {"id": None}

    def _form_label(text: str, row: int, *, top: int = 8) -> None:
        ttk.Label(timed_form, text=text, style="Surface.TLabel").grid(
            row=row, column=0, sticky="w", pady=(top, 0)
        )

    # Row 0 — kind
    _form_label(t("sched.kind"), 0, top=0)
    kind_combo = ttk.Combobox(
        timed_form,
        textvariable=kind_var,
        values=[t(key) for _, key in TIMED_KINDS],
        state="readonly",
        width=22,
    )
    kind_combo.grid(row=0, column=1, sticky="ew", padx=(12, 0))

    # Row 1 — time
    _form_label(t("sched.time"), 1)
    ttk.Entry(timed_form, textvariable=time_var, width=10).grid(
        row=1, column=1, sticky="w", padx=(12, 0), pady=(8, 0)
    )

    # Optional kind fields (same label / input columns)
    once_label = ttk.Label(timed_form, text=t("sched.date"), style="Surface.TLabel")
    once_entry = ttk.Entry(timed_form, textvariable=date_var, width=14)

    weekly_label = ttk.Label(
        timed_form, text=t("sched.weekdays"), style="Surface.TLabel"
    )
    weekly_checks = tk.Frame(timed_form, bg=theme["surface"])
    for i, key in enumerate(WEEKDAY_KEYS):
        ttk.Checkbutton(
            weekly_checks,
            text=t(key),
            variable=weekday_vars[i],
            style="Surface.TCheckbutton",
        ).pack(side="left", padx=(0, 6))

    monthly_label = ttk.Label(
        timed_form, text=t("sched.day_of_month"), style="Surface.TLabel"
    )
    monthly_entry = ttk.Entry(timed_form, textvariable=day_var, width=8)

    yearly_label = ttk.Label(timed_form, text=t("sched.month"), style="Surface.TLabel")
    yearly_fields = tk.Frame(timed_form, bg=theme["surface"])
    ttk.Entry(yearly_fields, textvariable=month_var, width=6).pack(side="left")
    ttk.Label(
        yearly_fields, text=t("sched.day_of_month"), style="Surface.TLabel"
    ).pack(side="left", padx=(12, 0))
    ttk.Entry(yearly_fields, textvariable=day_var, width=6).pack(
        side="left", padx=(8, 0)
    )

    action_label = ttk.Label(timed_form, text=t("sched.action"), style="Surface.TLabel")
    action_combo = ttk.Combobox(
        timed_form,
        textvariable=action_var,
        values=[t(key) for _, key in ACTIONS],
        state="readonly",
        width=22,
    )

    enabled_row = ttk.Checkbutton(
        timed_form,
        text=t("sched.enabled"),
        variable=timed_enabled,
        style="Surface.TCheckbutton",
    )

    def _hide_optional():
        for w in (
            once_label,
            once_entry,
            weekly_label,
            weekly_checks,
            monthly_label,
            monthly_entry,
            yearly_label,
            yearly_fields,
            action_label,
            action_combo,
            enabled_row,
        ):
            w.grid_remove()

    def sync_kind_fields(_e=None):
        kind = kind_map.get(kind_var.get(), "daily")
        _hide_optional()
        next_row = 2
        if kind == "once":
            once_label.grid(row=next_row, column=0, sticky="w", pady=(8, 0))
            once_entry.grid(
                row=next_row, column=1, sticky="w", padx=(12, 0), pady=(8, 0)
            )
            next_row += 1
        elif kind == "weekly":
            weekly_label.grid(row=next_row, column=0, sticky="w", pady=(8, 0))
            weekly_checks.grid(
                row=next_row, column=1, sticky="w", padx=(12, 0), pady=(8, 0)
            )
            next_row += 1
        elif kind == "monthly":
            monthly_label.grid(row=next_row, column=0, sticky="w", pady=(8, 0))
            monthly_entry.grid(
                row=next_row, column=1, sticky="w", padx=(12, 0), pady=(8, 0)
            )
            next_row += 1
        elif kind == "yearly":
            yearly_label.grid(row=next_row, column=0, sticky="w", pady=(8, 0))
            yearly_fields.grid(
                row=next_row, column=1, sticky="w", padx=(12, 0), pady=(8, 0)
            )
            next_row += 1
        action_label.grid(row=next_row, column=0, sticky="w", pady=(8, 0))
        action_combo.grid(
            row=next_row, column=1, sticky="ew", padx=(12, 0), pady=(8, 0)
        )
        enabled_row.grid(
            row=next_row + 1, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

    kind_combo.bind("<<ComboboxSelected>>", sync_kind_fields)
    sync_kind_fields()

    # --- Loop tab ---
    tk.Label(
        loop_tab,
        text=t("sched.loop_blurb"),
        bg=theme["bg"],
        fg=theme["text_muted"],
        font=FONTS["subtitle"],
        wraplength=460,
        justify="left",
        anchor="w",
    ).grid(row=0, column=0, sticky="ew", pady=(0, 8))

    loop_list_wrap = tk.Frame(loop_tab, bg=theme["surface"], padx=8, pady=8)
    loop_list_wrap.grid(row=1, column=0, sticky="nsew")
    loop_list = tk.Listbox(
        loop_list_wrap,
        bg=theme["surface_2"],
        fg=theme["text"],
        selectbackground=theme["accent"],
        selectforeground=theme["accent_text"],
        font=FONTS["ui"],
        height=4,
        activestyle="none",
        borderwidth=0,
        highlightthickness=0,
    )
    loop_list.pack(fill="both", expand=True)
    loop_rules: list[dict] = []

    loop_form = tk.Frame(loop_tab, bg=theme["surface"], padx=10, pady=10)
    loop_form.grid(row=2, column=0, sticky="ew", pady=(8, 0))
    on_min_var = tk.StringVar(value="10")
    off_min_var = tk.StringVar(value="10")
    loop_enabled = tk.BooleanVar(value=True)
    loop_edit: dict[str, str | None] = {"id": None}

    row = tk.Frame(loop_form, bg=theme["surface"])
    row.pack(fill="x")
    ttk.Label(row, text=t("sched.on_minutes"), style="Surface.TLabel").pack(side="left")
    ttk.Entry(row, textvariable=on_min_var, width=6).pack(side="left", padx=(6, 16))
    ttk.Label(row, text=t("sched.off_minutes"), style="Surface.TLabel").pack(
        side="left"
    )
    ttk.Entry(row, textvariable=off_min_var, width=6).pack(side="left", padx=(6, 0))
    ttk.Checkbutton(
        loop_form,
        text=t("sched.enabled"),
        variable=loop_enabled,
        style="Surface.TCheckbutton",
    ).pack(anchor="w", pady=(10, 0))

    def reload():
        nonlocal all_rules, timed_rules, loop_rules
        all_rules = get_schedules(device["id"], socket)
        timed_rules = [r for r in all_rules if (r.get("kind") or "daily") != "loop"]
        loop_rules = [r for r in all_rules if (r.get("kind") or "") == "loop"]
        timed_list.delete(0, "end")
        for r in timed_rules:
            timed_list.insert("end", _summarize_timed(r))
        loop_list.delete(0, "end")
        for r in loop_rules:
            loop_list.insert("end", _summarize_loop(r))

    def clear_timed():
        timed_edit["id"] = None
        kind_var.set(t("sched.kind.daily"))
        time_var.set("08:00")
        date_var.set("")
        day_var.set("1")
        month_var.set("1")
        action_var.set(t("sched.action_on"))
        timed_enabled.set(True)
        for v in weekday_vars:
            v.set(False)
        sync_kind_fields()

    def clear_loop():
        loop_edit["id"] = None
        on_min_var.set("10")
        off_min_var.set("10")
        loop_enabled.set(True)

    def load_timed(_e=None):
        sel = timed_list.curselection()
        if not sel:
            return
        rule = timed_rules[sel[0]]
        timed_edit["id"] = rule.get("id")
        kind_var.set(_kind_label(rule.get("kind") or "daily"))
        time_var.set(rule.get("time") or "08:00")
        date_var.set(rule.get("date") or "")
        day_var.set(str(rule.get("day_of_month") or rule.get("day") or 1))
        month_var.set(str(rule.get("month") or 1))
        action_var.set(_action_label(rule.get("action") or "on"))
        timed_enabled.set(bool(rule.get("enabled", True)))
        selected = {int(d) for d in (rule.get("weekdays") or [])}
        for i, v in enumerate(weekday_vars):
            v.set(i in selected)
        sync_kind_fields()

    def load_loop(_e=None):
        sel = loop_list.curselection()
        if not sel:
            return
        rule = loop_rules[sel[0]]
        loop_edit["id"] = rule.get("id")
        on_min_var.set(str(rule.get("on_minutes") or 10))
        off_min_var.set(str(rule.get("off_minutes") or 10))
        loop_enabled.set(bool(rule.get("enabled", True)))

    timed_list.bind("<<ListboxSelect>>", load_timed)
    loop_list.bind("<<ListboxSelect>>", load_loop)

    def save_timed():
        kind = kind_map.get(kind_var.get(), "daily")
        try:
            rule = {
                "id": timed_edit["id"],
                "enabled": bool(timed_enabled.get()),
                "kind": kind,
                "time": (time_var.get() or "00:00").strip(),
                "action": action_map.get(action_var.get(), "on"),
            }
            if kind == "once":
                rule["date"] = (date_var.get() or "").strip()
                if not rule["date"]:
                    raise ValueError(t("sched.need_date"))
            if kind == "weekly":
                rule["weekdays"] = [i for i, v in enumerate(weekday_vars) if v.get()]
                if not rule["weekdays"]:
                    raise ValueError(t("sched.need_weekdays"))
            if kind == "monthly":
                rule["day_of_month"] = int(day_var.get() or 0)
            if kind == "yearly":
                rule["month"] = int(month_var.get() or 0)
                rule["day"] = int(day_var.get() or 0)
            upsert_schedule(device["id"], rule, socket=socket)
            _sync_device(device, socket)
            clear_timed()
            reload()
        except Exception as exc:
            messagebox.showerror(t("sched.title", name=title), str(exc), parent=win)

    def save_loop():
        try:
            rule = {
                "id": loop_edit["id"],
                "enabled": bool(loop_enabled.get()),
                "kind": "loop",
                "on_minutes": max(0, int(on_min_var.get() or 0)),
                "off_minutes": max(0, int(off_min_var.get() or 0)),
            }
            existing = next(
                (r for r in loop_rules if r.get("id") == loop_edit["id"]), None
            )
            if existing and existing.get("loop_start"):
                rule["loop_start"] = existing["loop_start"]
            else:
                rule["loop_start"] = datetime.now().isoformat(timespec="seconds")
            upsert_schedule(device["id"], rule, socket=socket)
            _sync_device(device, socket)
            clear_loop()
            reload()
        except Exception as exc:
            messagebox.showerror(t("sched.title", name=title), str(exc), parent=win)

    def delete_timed():
        sel = timed_list.curselection()
        if not sel:
            return
        rid = timed_rules[sel[0]].get("id")
        if not rid:
            return
        delete_schedule(device["id"], rid, socket=socket)
        _sync_device(device, socket)
        clear_timed()
        reload()

    def delete_loop():
        sel = loop_list.curselection()
        if not sel:
            return
        rid = loop_rules[sel[0]].get("id")
        if not rid:
            return
        delete_schedule(device["id"], rid, socket=socket)
        _sync_device(device, socket)
        clear_loop()
        reload()

    timed_btns = tk.Frame(timed_tab, bg=theme["bg"])
    timed_btns.grid(row=3, column=0, sticky="ew", pady=(10, 0))
    ttk.Button(
        timed_btns, text=t("sched.save"), style="Accent.TButton", command=save_timed
    ).pack(side="left")
    ttk.Button(
        timed_btns, text=t("sched.delete"), style="TButton", command=delete_timed
    ).pack(side="left", padx=(8, 0))
    ttk.Button(
        timed_btns, text=t("sched.new"), style="Ghost.TButton", command=clear_timed
    ).pack(side="left", padx=(8, 0))

    loop_btns = tk.Frame(loop_tab, bg=theme["bg"])
    loop_btns.grid(row=3, column=0, sticky="ew", pady=(10, 0))
    ttk.Button(
        loop_btns, text=t("sched.save"), style="Accent.TButton", command=save_loop
    ).pack(side="left")
    ttk.Button(
        loop_btns, text=t("sched.delete"), style="TButton", command=delete_loop
    ).pack(side="left", padx=(8, 0))
    ttk.Button(
        loop_btns, text=t("sched.new"), style="Ghost.TButton", command=clear_loop
    ).pack(side="left", padx=(8, 0))

    reload()
