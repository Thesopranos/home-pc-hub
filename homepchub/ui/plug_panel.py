"""Plug / strip feature panel - device-level or per-socket (child)."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from homepchub.core.config import update_alias
from homepchub.core.devices import get_plug_features, set_alias, set_plug_feature
from homepchub.i18n import t
from homepchub.i18n.labels import (
    category_label,
    feature_help,
    feature_label,
    format_display,
    type_label,
    ui_help,
)
from homepchub.ui.theme import FONTS, apply_ttk, get_theme
from homepchub.ui.tooltip import labeled_row
from homepchub.ui.schedule_panel import open_schedule_panel
from homepchub.ui.layout import ThemedVScrollbar, size_window
from homepchub.ui.winchrome import dress_window


def open_plug_panel(
    parent: tk.Misc,
    device: dict,
    theme_mode: str,
    *,
    socket: int | None = None,
    on_close=None,
) -> None:
    theme = get_theme(theme_mode)
    win = tk.Toplevel(parent)
    base = device.get("alias") or device["host"]
    sock_name = None
    if socket is not None:
        for s in device.get("sockets") or []:
            if int(s["index"]) == socket:
                sock_name = s.get("alias") or t("status.socket_n", n=socket + 1)
                break
        if sock_name is None:
            sock_name = t("status.socket_label", n=socket + 1)
        title = f"{base} - {sock_name}"
        scope_hint = t("plug.scope_socket")
        current_name = sock_name
    elif device.get("kind") == "bulb" or device.get("has_light"):
        title = base
        scope_hint = t("plug.scope_bulb")
        current_name = base
    else:
        title = base
        scope_hint = t("plug.scope_device")
        current_name = device.get("alias") or ""

    win.title(t("plug.title", name=title))
    win.configure(bg=theme["bg"])
    win.resizable(True, True)
    win.transient(parent)
    win.grab_set()
    dress_window(win, theme, dark=theme_mode == "dark")
    size_window(win, 420, 520, min_width=360, min_height=400)

    style = ttk.Style(win)
    apply_ttk(style, theme)

    root = tk.Frame(win, bg=theme["bg"], padx=20, pady=16)
    root.pack(fill="both", expand=True)

    title_lbl = tk.Label(
        root,
        text=title,
        bg=theme["bg"],
        fg=theme["text"],
        font=FONTS["title"],
        anchor="w",
    )
    title_lbl.pack(fill="x")
    tk.Label(
        root,
        text=scope_hint,
        bg=theme["bg"],
        fg=theme["text_muted"],
        font=FONTS["subtitle"],
        anchor="w",
        wraplength=360,
        justify="left",
    ).pack(fill="x", pady=(2, 10))

    # --- Rename (device or outlet) ---
    edit = tk.Frame(root, bg=theme["surface"], padx=12, pady=10)
    edit.pack(fill="x", pady=(0, 10))
    labeled_row(
        edit,
        t("plug.name"),
        ui_help("rename"),
        bg=theme["surface"],
        fg=theme["text"],
        muted=theme["text_muted"],
        accent=theme["accent"],
        font_title=FONTS["ui_bold"],
    ).pack(anchor="w", fill="x")
    name_row = tk.Frame(edit, bg=theme["surface"])
    name_row.pack(fill="x", pady=(6, 0))
    name_var = tk.StringVar(
        value=current_name if current_name != device["host"] else ""
    )
    name_entry = ttk.Entry(name_row, textvariable=name_var)
    name_entry.pack(side="left", fill="x", expand=True)
    renamed = {"ok": False}

    def save_name():
        new_name = name_var.get().strip()
        if not new_name:
            status.set(t("plug.name_empty"))
            return
        status.set(t("plug.setting"))

        def go():
            try:
                cleaned = set_alias(device["host"], new_name, socket=socket)
                update_alias(device["id"], cleaned, socket=socket)
                if socket is None:
                    device["alias"] = cleaned
                else:
                    sockets = list(device.get("sockets") or [])
                    found = False
                    for s in sockets:
                        if int(s["index"]) == int(socket):
                            s["alias"] = cleaned
                            found = True
                            break
                    if not found:
                        sockets.append({"index": int(socket), "alias": cleaned})
                    device["sockets"] = sockets
                renamed["ok"] = True

                def done():
                    if socket is None:
                        title_lbl.configure(text=cleaned)
                        win.title(t("plug.title", name=cleaned))
                    else:
                        new_title = f"{device.get('alias') or device['host']} - {cleaned}"
                        title_lbl.configure(text=new_title)
                        win.title(t("plug.title", name=new_title))
                    status.set(t("plug.name_saved"))

                win.after(0, done)
            except Exception as exc:
                win.after(0, lambda: status.set(t("status.error", error=exc)))

        threading.Thread(target=go, daemon=True).start()

    ttk.Button(
        name_row, text=t("plug.save_name"), style="Accent.TButton", command=save_name
    ).pack(side="right", padx=(8, 0))

    is_bulb_details = socket is None and (
        device.get("kind") == "bulb" or device.get("has_light")
    )
    if not is_bulb_details:
        sched_row = tk.Frame(root, bg=theme["bg"])
        sched_row.pack(fill="x", pady=(0, 10))
        ttk.Button(
            sched_row,
            text=t("sched.open"),
            style="TButton",
            command=lambda: open_schedule_panel(
                win, device, theme_mode, socket=socket
            ),
        ).pack(anchor="w")

    status = tk.StringVar(value=t("plug.loading"))
    tk.Label(
        root,
        textvariable=status,
        bg=theme["bg"],
        fg=theme["text_muted"],
        font=FONTS["subtitle"],
        anchor="w",
    ).pack(fill="x", pady=(0, 8))

    def close():
        try:
            win.unbind("<MouseWheel>")
        except tk.TclError:
            pass
        win.grab_release()
        win.destroy()
        if on_close:
            on_close(renamed=renamed["ok"])

    footer = tk.Frame(root, bg=theme["bg"])
    footer.pack(side="bottom", fill="x", pady=(12, 0))
    ttk.Button(
        footer, text=t("plug.close"), style="Ghost.TButton", command=close
    ).pack(anchor="e")

    outer = tk.Frame(root, bg=theme["surface"])
    outer.pack(fill="both", expand=True)

    canvas = tk.Canvas(outer, bg=theme["surface"], highlightthickness=0, bd=0)
    scroll = ThemedVScrollbar(outer, theme, command=canvas.yview)
    body = tk.Frame(canvas, bg=theme["surface"], padx=14, pady=12)
    win_id = canvas.create_window((0, 0), window=body, anchor="nw")

    def _update_scrollregion(_event=None):
        canvas.update_idletasks()
        bbox = canvas.bbox("all")
        if bbox:
            canvas.configure(scrollregion=bbox)

    def _stretch(event):
        canvas.itemconfigure(win_id, width=max(event.width, 1))
        _update_scrollregion()

    body.bind("<Configure>", _update_scrollregion)
    canvas.bind("<Configure>", _stretch)
    canvas.configure(yscrollcommand=scroll.set)
    canvas.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    def _on_mousewheel(event):
        if event.delta:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _bind_mousewheel(widget):
        widget.bind("<MouseWheel>", _on_mousewheel)
        for child in widget.winfo_children():
            _bind_mousewheel(child)

    for w in (win, outer, canvas, body):
        w.bind("<MouseWheel>", _on_mousewheel)

    loading = tk.Label(
        body,
        text=t("plug.loading"),
        bg=theme["surface"],
        fg=theme["text_muted"],
        font=FONTS["ui"],
    )
    loading.pack(pady=24)

    def worker():
        try:
            data = get_plug_features(device["host"], socket=socket)
            win.after(0, lambda: build(data))
        except Exception as exc:
            win.after(0, lambda: fail(str(exc)))

    def fail(msg: str):
        loading.destroy()
        messagebox.showerror(
            t("plug.title", name=title), t("plug.error", error=msg), parent=win
        )
        close()

    def finish_layout():
        _update_scrollregion()
        _bind_mousewheel(body)
        canvas.yview_moveto(0)

    def build(data: dict):
        loading.destroy()
        live_alias = (data.get("alias") or "").strip()
        if live_alias and not name_var.get().strip():
            name_var.set(live_alias)

        feats = data.get("features") or []
        if not feats:
            tk.Label(
                body,
                text=t("plug.empty"),
                bg=theme["surface"],
                fg=theme["text_muted"],
                font=FONTS["subtitle"],
                justify="left",
            ).pack(anchor="w", pady=12)
            status.set(t("plug.ready"))
            finish_layout()
            return

        host = device["host"]

        for feat in feats:
            row = tk.Frame(body, bg=theme["surface"])
            row.pack(fill="x", pady=6)

            left = tk.Frame(row, bg=theme["surface"])
            left.pack(side="left", fill="x", expand=True)
            meta_parts = []
            if feat.get("category"):
                meta_parts.append(category_label(feat["category"]))
            if feat.get("type"):
                meta_parts.append(type_label(feat["type"]))
            meta = " · ".join(p for p in meta_parts if p)
            labeled_row(
                left,
                feature_label(feat.get("id"), feat.get("name")),
                feature_help(feat.get("id"), feat.get("name")),
                bg=theme["surface"],
                fg=theme["text"],
                muted=theme["text_muted"],
                accent=theme["accent"],
                font_title=FONTS["ui_bold"],
                font_meta=FONTS["subtitle"],
                meta=meta or None,
            ).pack(anchor="w", fill="x")

            ftype = feat["type"]
            fid = feat["id"]
            unit = feat.get("unit") or ""

            if ftype in ("Sensor", "BinarySensor") or not feat.get("writable"):
                text = format_display(feat.get("value"), feat.get("unit"))
                tk.Label(
                    row,
                    text=text,
                    bg=theme["surface"],
                    fg=theme["accent"],
                    font=FONTS["meta"],
                    anchor="e",
                ).pack(side="right")
                continue

            if ftype == "Switch":
                var = tk.BooleanVar(value=bool(feat.get("value")))

                def on_switch(v=var, feature_id=fid):
                    status.set(t("plug.setting"))

                    def go():
                        try:
                            set_plug_feature(host, feature_id, v.get(), socket=socket)
                            win.after(0, lambda: status.set(t("plug.ready")))
                        except Exception as exc:
                            win.after(
                                0, lambda: status.set(t("status.error", error=exc))
                            )

                    threading.Thread(target=go, daemon=True).start()

                ttk.Checkbutton(row, variable=var, command=on_switch).pack(side="right")
                continue

            if ftype == "Number":
                vmin = float(feat.get("minimum") or 0)
                vmax = float(feat.get("maximum") or 100)
                cur = feat.get("value")
                try:
                    cur = float(cur)
                except (TypeError, ValueError):
                    cur = vmin
                var = tk.DoubleVar(value=cur)
                read = tk.Label(
                    row,
                    text=format_display(cur, unit),
                    bg=theme["surface"],
                    fg=theme["accent"],
                    font=FONTS["meta"],
                    width=10,
                    anchor="e",
                )
                read.pack(side="right")

                def on_move(_=None, v=var, r=read, u=unit):
                    r.configure(text=format_display(float(v.get()), u))

                def on_release(_=None, v=var, feature_id=fid):
                    status.set(t("plug.setting"))
                    val = float(v.get())

                    def go():
                        try:
                            set_plug_feature(host, feature_id, val, socket=socket)
                            win.after(0, lambda: status.set(t("plug.ready")))
                        except Exception as exc:
                            win.after(
                                0, lambda: status.set(t("status.error", error=exc))
                            )

                    threading.Thread(target=go, daemon=True).start()

                scale = ttk.Scale(
                    row, from_=vmin, to=vmax, variable=var, command=on_move
                )
                scale.pack(side="right", fill="x", expand=True, padx=(8, 8))
                scale.bind("<ButtonRelease-1>", on_release)
                continue

            if ftype == "Choice":
                choices = [format_display(c) for c in (feat.get("choices") or [])]
                raw_choices = [str(c) for c in (feat.get("choices") or [])]
                display_to_raw = dict(zip(choices, raw_choices))
                current_disp = format_display(feat.get("value"))
                var = tk.StringVar(value=current_disp)
                box = ttk.Combobox(
                    row, textvariable=var, values=choices, state="readonly", width=14
                )
                box.pack(side="right")

                def on_choice(_e=None, v=var, feature_id=fid, mapping=display_to_raw):
                    status.set(t("plug.setting"))
                    raw = mapping.get(v.get(), v.get())

                    def go():
                        try:
                            set_plug_feature(host, feature_id, raw, socket=socket)
                            win.after(0, lambda: status.set(t("plug.ready")))
                        except Exception as exc:
                            win.after(
                                0, lambda: status.set(t("status.error", error=exc))
                            )

                    threading.Thread(target=go, daemon=True).start()

                box.bind("<<ComboboxSelected>>", on_choice)
                continue

            if ftype == "Action":

                def on_action(feature_id=fid):
                    status.set(t("plug.running"))

                    def go():
                        try:
                            set_plug_feature(host, feature_id, True, socket=socket)
                            win.after(0, lambda: status.set(t("plug.ready")))
                        except Exception as exc:
                            win.after(
                                0, lambda: status.set(t("status.error", error=exc))
                            )

                    threading.Thread(target=go, daemon=True).start()

                ttk.Button(
                    row, text=t("plug.run"), style="TButton", command=on_action
                ).pack(side="right")
                continue

            tk.Label(
                row,
                text=format_display(feat.get("value"), unit),
                bg=theme["surface"],
                fg=theme["text_muted"],
                font=FONTS["meta"],
            ).pack(side="right")

        status.set(t("plug.ready_n", count=len(feats)))
        finish_layout()

    threading.Thread(target=worker, daemon=True).start()
