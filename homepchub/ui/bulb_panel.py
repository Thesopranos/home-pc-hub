"""Bulb feature panel — shows only capabilities the device reports."""

from __future__ import annotations

import colorsys
import math
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from PIL import Image, ImageTk

from homepchub.core.devices import (
    get_light_state,
    set_alias,
    set_light_brightness,
    set_light_color_temp,
    set_light_hsv,
    set_power,
)
from homepchub.core import presets as bulb_presets
from homepchub.core.config import (
    get_screen_sync_boost,
    get_screen_sync_monitor,
    set_screen_sync_settings,
    update_alias,
)
from homepchub.core.monitors import list_monitors, show_monitor_identifiers
from homepchub.i18n import t
from homepchub.ui.preset_picker import add_preset_select
from homepchub.ui.plug_panel import open_plug_panel
from homepchub.i18n.labels import light_feat_label, ui_help
from homepchub.ui.theme import FONTS, apply_ttk, get_theme
from homepchub.ui.winchrome import dress_window
from homepchub.ui.tooltip import labeled_row
from homepchub.ui.layout import make_scroll_body, size_window

WHEEL_SIZE = 200
_wheel_cache: dict[str, Image.Image] = {}


def _hsv_to_hex(h: float, s: float, v: float) -> str:
    r, g, b = colorsys.hsv_to_rgb(h / 360.0, s / 100.0, v / 100.0)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def _hex_to_rgb(hx: str) -> tuple[int, int, int]:
    hx = hx.lstrip("#")
    return int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)


def _make_color_wheel(bg_hex: str) -> Image.Image:
    if bg_hex in _wheel_cache:
        return _wheel_cache[bg_hex]
    size = WHEEL_SIZE
    cx = cy = size / 2
    r_max = size / 2 - 2
    bg = _hex_to_rgb(bg_hex)
    img = Image.new("RGB", (size, size), bg)
    pixels = img.load()
    for y in range(size):
        dy = y - cy
        for x in range(size):
            dx = x - cx
            r = math.hypot(dx, dy)
            if r <= r_max:
                angle = (math.degrees(math.atan2(dy, dx)) + 360) % 360
                sat = min(r / r_max, 1.0)
                rr, gg, bb = colorsys.hsv_to_rgb(angle / 360, sat, 1.0)
                pixels[x, y] = (int(rr * 255), int(gg * 255), int(bb * 255))
    _wheel_cache[bg_hex] = img
    return img


def _wheel_to_hs(x: float, y: float) -> tuple[float, float]:
    cx = cy = WHEEL_SIZE / 2
    r_max = WHEEL_SIZE / 2 - 2
    dx, dy = x - cx, y - cy
    r = min(math.hypot(dx, dy), r_max)
    angle = (math.degrees(math.atan2(dy, dx)) + 360) % 360
    sat = (r / r_max) * 100 if r_max else 0
    return angle, sat


def open_bulb_panel(
    parent: tk.Tk, device: dict, theme_mode: str, *, on_close=None
) -> None:
    theme = get_theme(theme_mode)
    win = tk.Toplevel(parent)
    title = device.get("alias") or device["host"]
    win.title(t("bulb.title", name=title))
    win.configure(bg=theme["bg"])
    win.resizable(True, True)
    win.transient(parent)
    win.grab_set()
    dress_window(win, theme, dark=theme_mode == "dark")
    size_window(win, 480, 640, min_width=400, min_height=480)

    style = ttk.Style(win)
    apply_ttk(style, theme)

    root = tk.Frame(win, bg=theme["bg"], padx=20, pady=16)
    root.pack(fill="both", expand=True)

    head = tk.Frame(root, bg=theme["bg"])
    head.pack(fill="x")
    titles = tk.Frame(head, bg=theme["bg"])
    titles.pack(side="left", fill="x", expand=True)
    title_lbl = tk.Label(
        titles,
        text=title,
        bg=theme["bg"],
        fg=theme["text"],
        font=FONTS["title"],
        anchor="w",
    )
    title_lbl.pack(fill="x")
    tk.Label(
        titles,
        text=f"{device.get('model') or '—'}  ·  {device['host']}",
        bg=theme["bg"],
        fg=theme["text_muted"],
        font=FONTS["meta"],
        anchor="w",
    ).pack(fill="x", pady=(2, 0))

    renamed = {"ok": False}

    def apply_title(name: str):
        title_lbl.configure(text=name)
        win.title(t("bulb.title", name=name))

    def open_device_details():
        # nested modal: release bulb grab, restore when details close
        win.grab_release()

        def after_details(**kw):
            if kw.get("renamed"):
                renamed["ok"] = True
                name = device.get("alias") or device["host"]
                apply_title(name)
                name_var.set(name)
            if win.winfo_exists():
                win.grab_set()

        open_plug_panel(
            win,
            device,
            theme_mode,
            socket=None,
            on_close=after_details,
        )

    ttk.Button(
        head,
        text="···",
        style="Ghost.TButton",
        width=3,
        command=open_device_details,
    ).pack(side="right", padx=(8, 0))

    # --- Rename (Tapo device alias) ---
    edit = tk.Frame(root, bg=theme["surface"], padx=12, pady=10)
    edit.pack(fill="x", pady=(12, 0))
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
        value=title if title != device["host"] else (device.get("alias") or "")
    )
    ttk.Entry(name_row, textvariable=name_var).pack(side="left", fill="x", expand=True)

    def save_name():
        new_name = name_var.get().strip()
        if not new_name:
            status.set(t("plug.name_empty"))
            return
        status.set(t("plug.setting"))

        def go():
            try:
                cleaned = set_alias(device["host"], new_name, socket=None)
                update_alias(device["id"], cleaned, socket=None)
                device["alias"] = cleaned
                renamed["ok"] = True

                def done():
                    apply_title(cleaned)
                    status.set(t("plug.name_saved"))

                win.after(0, done)
            except Exception as exc:
                win.after(0, lambda: status.set(t("status.error", error=exc)))

        threading.Thread(target=go, daemon=True).start()

    ttk.Button(
        name_row, text=t("plug.save_name"), style="Accent.TButton", command=save_name
    ).pack(side="right", padx=(8, 0))

    status = tk.StringVar(value=t("bulb.loading"))
    tk.Label(
        root,
        textvariable=status,
        bg=theme["bg"],
        fg=theme["text_muted"],
        font=FONTS["subtitle"],
        anchor="w",
    ).pack(fill="x", pady=(12, 8))

    def close():
        win.grab_release()
        win.destroy()
        if on_close:
            on_close(renamed=renamed["ok"])

    footer = tk.Frame(root, bg=theme["bg"])
    footer.pack(side="bottom", fill="x", pady=(8, 0))
    ttk.Button(
        footer, text=t("bulb.close"), style="Ghost.TButton", command=close
    ).pack(anchor="e")

    scroll_outer, _canvas, body = make_scroll_body(root, theme)
    scroll_outer.pack(fill="both", expand=True)

    loading = tk.Label(
        body,
        text=t("bulb.loading"),
        bg=theme["surface"],
        fg=theme["text_muted"],
        font=FONTS["ui"],
    )
    loading.pack(pady=20)

    def worker():
        try:
            state = get_light_state(device["host"])
            win.after(0, lambda: build(state))
        except Exception as exc:
            win.after(0, lambda: fail(str(exc)))

    def fail(msg: str):
        loading.destroy()
        messagebox.showerror(
            t("bulb.title", name=title), t("bulb.error", error=msg), parent=win
        )
        close()

    def build(state: dict):
        loading.destroy()
        if not state.get("supported"):
            messagebox.showinfo(
                t("bulb.title", name=title),
                t("bulb.unsupported"),
                parent=win,
            )
            close()
            return

        feats = state["features"]
        host = device["host"]

        # Power
        power_row = tk.Frame(body, bg=theme["surface"])
        power_row.pack(fill="x", pady=(0, 12))
        labeled_row(
            power_row,
            t("bulb.power"),
            ui_help("power"),
            bg=theme["surface"],
            fg=theme["text"],
            muted=theme["text_muted"],
            accent=theme["accent"],
            font_title=FONTS["ui_bold"],
        ).pack(side="left")
        power_var = tk.BooleanVar(value=bool(state.get("is_on")))

        def on_power():
            on = power_var.get()
            status.set(t("bulb.powering"))

            def go():
                try:
                    set_power(host, on)
                    win.after(0, lambda: status.set(t("status.ready")))
                except Exception as exc:
                    win.after(0, lambda: status.set(t("status.error", error=exc)))

            threading.Thread(target=go, daemon=True).start()

        ttk.Checkbutton(
            power_row, text=t("bulb.on"), variable=power_var, command=on_power
        ).pack(side="right")

        # Ambient presets (reading, work, … — each mode is a registered module)
        preset_ids = bulb_presets.list_preset_ids()
        if preset_ids and (feats.get("color_temp") or feats.get("brightness")):
            section(body, theme, t("preset.section"), ui_help("presets"))
            preset_row = add_preset_select(
                body,
                host=host,
                device_id=device.get("id"),
                active_preset=device.get("active_preset"),
                after=win.after,
                status_set=status.set,
                theme=theme,
                width=28,
            )
            if preset_row is not None:
                preset_row.pack(fill="x", pady=(0, 10))

            # Screen Sync: pick monitor + Identify (Home Hub style)
            sync_row = tk.Frame(body, bg=theme["surface"])
            sync_row.pack(fill="x", pady=(4, 0))
            tk.Label(
                sync_row,
                text=t("preset.screen_sync_monitor"),
                bg=theme["surface"],
                fg=theme["text"],
                font=FONTS["ui"],
            ).pack(side="left", padx=(0, 8))
            monitors = list_monitors()
            monitor_names = [
                t("preset.screen_n", n=i + 1) for i in range(len(monitors))
            ] or [t("preset.screen_n", n=1)]
            saved_mon = get_screen_sync_monitor()
            mon_idx = (
                saved_mon if 0 <= saved_mon < len(monitor_names) else 0
            )
            monitor_var = tk.StringVar(value=monitor_names[mon_idx])
            monitor_combo = ttk.Combobox(
                sync_row,
                textvariable=monitor_var,
                values=monitor_names,
                state="readonly",
                width=12,
            )
            monitor_combo.set(monitor_names[mon_idx])
            monitor_combo.pack(side="left")

            def on_monitor_change(_e=None):
                name = monitor_var.get()
                try:
                    idx = monitor_names.index(name)
                except ValueError:
                    idx = monitor_combo.current()
                if idx < 0:
                    return
                set_screen_sync_settings(monitor=idx)
                monitor_combo.set(monitor_names[idx])
                status.set(t("preset.screen_sync_saved"))

            monitor_combo.bind("<<ComboboxSelected>>", on_monitor_change)
            ttk.Button(
                sync_row,
                text=t("preset.identify"),
                style="Ghost.TButton",
                command=lambda: show_monitor_identifiers(win),
            ).pack(side="left", padx=(8, 0))

            boost_row = tk.Frame(body, bg=theme["surface"])
            boost_row.pack(fill="x", pady=(6, 10))
            tk.Label(
                boost_row,
                text=t("preset.screen_sync_boost"),
                bg=theme["surface"],
                fg=theme["text"],
                font=FONTS["ui"],
            ).pack(side="left", padx=(0, 8))
            boost_var = tk.StringVar(value=str(get_screen_sync_boost()))
            boost_entry = ttk.Entry(boost_row, textvariable=boost_var, width=6)
            boost_entry.pack(side="left")

            def on_boost_save(_e=None):
                try:
                    boost = max(0, min(100, int(boost_var.get().strip())))
                except ValueError:
                    status.set(t("preset.boost_invalid"))
                    return
                boost_var.set(str(boost))
                set_screen_sync_settings(boost=boost)
                status.set(t("preset.screen_sync_saved"))

            boost_entry.bind("<Return>", on_boost_save)
            boost_entry.bind("<FocusOut>", on_boost_save)

        # Brightness
        if feats.get("brightness"):
            section(body, theme, t("bulb.brightness"), ui_help("brightness"))
            bright = tk.IntVar(value=int(state.get("brightness") or 50))
            bright_lbl = tk.Label(
                body,
                text=f"{bright.get()}%",
                bg=theme["surface"],
                fg=theme["accent"],
                font=FONTS["meta"],
            )
            bright_lbl.pack(anchor="e")

            def on_bright(_=None):
                bright_lbl.configure(text=f"{int(float(bright.get()))}%")

            def apply_bright(_=None):
                val = int(float(bright.get()))
                status.set(t("bulb.brightness_set"))

                def go():
                    try:
                        set_light_brightness(host, val)
                        win.after(0, lambda: status.set(t("status.ready")))
                    except Exception as exc:
                        win.after(0, lambda: status.set(t("status.error", error=exc)))

                threading.Thread(target=go, daemon=True).start()

            scale = ttk.Scale(
                body, from_=1, to=100, variable=bright, command=on_bright
            )
            scale.pack(fill="x", pady=(0, 4))
            scale.bind("<ButtonRelease-1>", apply_bright)

        # Color temperature
        if feats.get("color_temp"):
            section(body, theme, t("bulb.color_temp"), ui_help("color_temp"))
            rng = state.get("color_temp_range") or {"min": 2500, "max": 6500}
            tmin, tmax = int(rng["min"]), int(rng["max"])
            cur = int(state.get("color_temp") or tmin)
            cur = max(tmin, min(tmax, cur))
            temp = tk.IntVar(value=cur)
            temp_lbl = tk.Label(
                body,
                text=f"{cur} K",
                bg=theme["surface"],
                fg=theme["accent"],
                font=FONTS["meta"],
            )
            temp_lbl.pack(anchor="e")

            def on_temp(_=None):
                temp_lbl.configure(text=f"{int(float(temp.get()))} K")

            def apply_temp(_=None):
                val = int(float(temp.get()))
                status.set(t("bulb.temp_set"))

                def go():
                    try:
                        set_light_color_temp(host, val)
                        win.after(0, lambda: status.set(t("status.ready")))
                    except Exception as exc:
                        win.after(0, lambda: status.set(t("status.error", error=exc)))

                threading.Thread(target=go, daemon=True).start()

            tscale = ttk.Scale(
                body, from_=tmin, to=tmax, variable=temp, command=on_temp
            )
            tscale.pack(fill="x", pady=(0, 4))
            tscale.bind("<ButtonRelease-1>", apply_temp)
            tk.Label(
                body,
                text=f"{tmin} K — {tmax} K",
                bg=theme["surface"],
                fg=theme["text_muted"],
                font=FONTS["subtitle"],
            ).pack(anchor="w", pady=(0, 8))

        # HSV color
        if feats.get("hsv"):
            section(body, theme, t("bulb.color"), ui_help("color"))
            hsv = state.get("hsv") or {"hue": 0, "saturation": 100, "value": 100}
            hue = tk.IntVar(value=int(hsv["hue"]))
            sat = tk.IntVar(value=int(hsv["saturation"]))
            val = tk.IntVar(value=int(hsv["value"]))

            picker_row = tk.Frame(body, bg=theme["surface"])
            picker_row.pack(fill="x", pady=(0, 8))

            wheel_img = _make_color_wheel(theme["surface"])
            wheel_photo = ImageTk.PhotoImage(wheel_img)
            win._wheel_photo = wheel_photo  # keep ref

            wheel = tk.Canvas(
                picker_row,
                width=WHEEL_SIZE,
                height=WHEEL_SIZE,
                highlightthickness=0,
                bg=theme["surface"],
                cursor="crosshair",
            )
            wheel.pack(side="left")
            wheel.create_image(0, 0, anchor="nw", image=wheel_photo)
            marker = wheel.create_oval(0, 0, 0, 0, outline="#ffffff", width=2)

            side = tk.Frame(picker_row, bg=theme["surface"])
            side.pack(side="left", fill="y", padx=(16, 0))

            preview = tk.Canvas(
                side, width=64, height=64, highlightthickness=0, bg=theme["surface"]
            )
            preview.pack(anchor="w")
            swatch = preview.create_oval(4, 4, 60, 60, fill="#ffffff", outline="")

            tk.Label(
                side,
                text=t("bulb.wheel_hint"),
                bg=theme["surface"],
                fg=theme["text_muted"],
                font=FONTS["subtitle"],
                justify="left",
                anchor="w",
            ).pack(anchor="w", pady=(10, 0))

            slider_reads: dict[str, tk.Label] = {}

            def place_marker():
                h = float(hue.get())
                s = float(sat.get()) / 100.0
                cx = cy = WHEEL_SIZE / 2
                r_max = WHEEL_SIZE / 2 - 2
                rad = math.radians(h)
                px = cx + math.cos(rad) * r_max * s
                py = cy + math.sin(rad) * r_max * s
                r = 7
                wheel.coords(marker, px - r, py - r, px + r, py + r)

            def refresh_preview(_=None):
                hx = _hsv_to_hex(
                    float(hue.get()), float(sat.get()), float(val.get())
                )
                preview.itemconfigure(swatch, fill=hx)
                place_marker()
                if "h" in slider_reads:
                    slider_reads["h"].configure(text=str(int(float(hue.get()))))
                if "s" in slider_reads:
                    slider_reads["s"].configure(text=str(int(float(sat.get()))))
                if "v" in slider_reads:
                    slider_reads["v"].configure(text=str(int(float(val.get()))))

            def apply_hsv(_=None):
                status.set(t("bulb.color_set"))
                h = int(float(hue.get()))
                s = int(float(sat.get()))
                v = int(float(val.get()))

                def go():
                    try:
                        set_light_hsv(host, h, s, v)
                        win.after(0, lambda: status.set(t("status.ready")))
                    except Exception as exc:
                        win.after(0, lambda: status.set(t("status.error", error=exc)))

                threading.Thread(target=go, daemon=True).start()

            def on_wheel_drag(event):
                h, s = _wheel_to_hs(event.x, event.y)
                hue.set(int(h))
                sat.set(int(s))
                refresh_preview()

            def on_wheel_release(event):
                on_wheel_drag(event)
                apply_hsv()

            wheel.bind("<Button-1>", on_wheel_drag)
            wheel.bind("<B1-Motion>", on_wheel_drag)
            wheel.bind("<ButtonRelease-1>", on_wheel_release)

            def slider(label, var, to, key, help_key):
                row = tk.Frame(body, bg=theme["surface"])
                row.pack(fill="x", pady=2)
                name_box = tk.Frame(row, bg=theme["surface"])
                name_box.pack(side="left")
                tk.Label(
                    name_box,
                    text=label,
                    anchor="w",
                    bg=theme["surface"],
                    fg=theme["text"],
                    font=FONTS["subtitle"],
                ).pack(side="left")
                from homepchub.ui.tooltip import attach_info_icon

                attach_info_icon(
                    name_box,
                    ui_help(help_key),
                    bg=theme["surface"],
                    fg=theme["text_muted"],
                    accent=theme["accent"],
                ).pack(side="left", padx=(4, 0))
                read = tk.Label(
                    row,
                    text=str(int(float(var.get()))),
                    width=4,
                    anchor="e",
                    bg=theme["surface"],
                    fg=theme["accent"],
                    font=FONTS["meta"],
                )
                read.pack(side="right")
                slider_reads[key] = read

                def on_move(_=None):
                    refresh_preview()

                sc = ttk.Scale(row, from_=0, to=to, variable=var, command=on_move)
                sc.pack(side="left", fill="x", expand=True, padx=8)
                return sc

            h_scale = slider(t("bulb.hue"), hue, 360, "h", "hue")
            s_scale = slider(t("bulb.sat"), sat, 100, "s", "saturation")
            v_scale = slider(t("bulb.val"), val, 100, "v", "value")

            for sc in (h_scale, s_scale, v_scale):
                sc.bind("<ButtonRelease-1>", apply_hsv)

            ttk.Button(
                body,
                text=t("bulb.apply_color"),
                style="Accent.TButton",
                command=apply_hsv,
            ).pack(anchor="e", pady=(8, 0))

            refresh_preview()

        # feature summary
        active = [light_feat_label(k) for k, v in feats.items() if v]
        feats_txt = ", ".join(active) if active else t("bulb.no_feats")
        status.set(t("bulb.ready_feats", feats=feats_txt))
        if hasattr(scroll_outer, "bind_wheel"):
            scroll_outer.bind_wheel()

    threading.Thread(target=worker, daemon=True).start()


def section(parent, theme, title: str, help_text: str = ""):
    labeled_row(
        parent,
        title,
        help_text or f"“{title}” ayar bölümü.",
        bg=theme["surface"],
        fg=theme["text"],
        muted=theme["text_muted"],
        accent=theme["accent"],
        font_title=FONTS["ui_bold"],
    ).pack(fill="x", pady=(8, 4))
