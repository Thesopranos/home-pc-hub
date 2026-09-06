import threading
import tkinter as tk
from tkinter import ttk, messagebox

from homepchub.assets import logo_photo
from homepchub.core.config import (
    add_device,
    get_theme_mode,
    load_config,
    merge_sockets,
    remove_device,
    save_config,
    set_theme,
    socket_identity,
)
from homepchub.core.devices import drop_cache, get_status, get_statuses, scan, set_power
from homepchub.ui.bulb_panel import open_bulb_panel
from homepchub.ui.plug_panel import open_plug_panel
from homepchub.i18n import get_lang, set_lang, t
from homepchub.i18n.labels import kind_label, ui_help
from homepchub.ui.theme import FONTS, apply_ttk, get_theme
from homepchub.ui.tooltip import attach_info_icon, labeled_row
from homepchub.ui.layout import ThemedVScrollbar, size_window
from homepchub.ui.preset_editor import open_preset_editor
from homepchub.ui.hotkey_panel import open_hotkey_panel
from homepchub.ui.winchrome import dress_window

STATUS_POLL_MS = 5000


class ToggleSwitch(tk.Canvas):
    """Pill toggle drawn on canvas — not a stock ttk checkbutton."""

    WIDTH = 46
    HEIGHT = 26
    PAD = 3
    KNOB = 20

    def __init__(self, parent, theme: dict, on_toggle=None, state=False, **kwargs):
        super().__init__(
            parent,
            width=self.WIDTH,
            height=self.HEIGHT,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            **kwargs,
        )
        self.theme = theme
        self.on_toggle = on_toggle
        self._on = bool(state)
        self._suppress = False
        self.bind("<Button-1>", self._clicked)
        self._draw()

    @property
    def var(self):
        # compatibility for strip summary that used BooleanVar
        class _V:
            def __init__(self, outer):
                self._o = outer

            def get(self):
                return self._o._on

        return _V(self)

    def set_theme(self, theme: dict):
        self.theme = theme
        self._draw()

    def set_state(self, on: bool):
        self._suppress = True
        self._on = bool(on)
        self._draw()
        self._suppress = False

    def _clicked(self, _event=None):
        if self._suppress:
            return
        self._on = not self._on
        self._draw()
        if self.on_toggle:
            self.on_toggle(self._on)

    def _draw(self):
        self.delete("all")
        track = self.theme["accent"] if self._on else self.theme["track_off"]
        bg = getattr(self, "_bg", self.theme["surface_2"])
        self.configure(bg=bg)
        r = self.HEIGHT / 2
        self.create_oval(0, 0, self.HEIGHT, self.HEIGHT, fill=track, outline="")
        self.create_oval(
            self.WIDTH - self.HEIGHT,
            0,
            self.WIDTH,
            self.HEIGHT,
            fill=track,
            outline="",
        )
        self.create_rectangle(
            r, 0, self.WIDTH - r, self.HEIGHT, fill=track, outline=""
        )
        kx = self.WIDTH - self.PAD - self.KNOB if self._on else self.PAD
        self.create_oval(
            kx,
            self.PAD,
            kx + self.KNOB,
            self.PAD + self.KNOB,
            fill=self.theme["knob"],
            outline="",
        )


class DeviceCard(tk.Frame):
    def __init__(self, parent, theme: dict, selected: bool = False, on_click=None):
        border = theme["accent"] if selected else theme["border"]
        super().__init__(parent, bg=border, padx=1, pady=1)
        self.theme = theme
        self.on_click = on_click
        self.inner = tk.Frame(self, bg=theme["surface_2"], padx=14, pady=12)
        self.inner.pack(fill="both", expand=True)
        for w in (self, self.inner):
            w.bind("<Button-1>", self._click)

    def _click(self, _e=None):
        if self.on_click:
            self.on_click()

    def set_selected(self, selected: bool):
        border = self.theme["accent"] if selected else self.theme["border"]
        self.configure(bg=border)

    def set_theme(self, theme: dict, selected: bool):
        self.theme = theme
        self.set_selected(selected)
        self.inner.configure(bg=theme["surface_2"])


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Home Pc Hub")
        size_window(self.root, 720, 680, min_width=560, min_height=560)

        self.mode = get_theme_mode()
        self.theme = get_theme(self.mode)
        self.style = ttk.Style(root)

        self.status = tk.StringVar(value=t("status.ready"))
        self._device_rows: dict[str, dict] = {}
        self._scan_hits: list[dict] = []
        self._selected_id: str | None = None
        self._expanded_ids: set[str] = set()
        self._theme_widgets: list = []
        self._logo_photo = None
        self._poll_after: str | None = None
        self._inflight = 0
        self._refreshing = False

        self._apply_root_theme()
        self._build()
        self.refresh_device_list()
        self._schedule_poll()

    def _apply_root_theme(self):
        self.theme = get_theme(self.mode)
        self.root.configure(bg=self.theme["bg"])
        apply_ttk(self.style, self.theme)
        dress_window(self.root, self.theme, dark=self.mode == "dark")

    def _rebuild_ui(self):
        selected = self._selected_id
        scan_hits = list(self._scan_hits)
        self._cancel_poll()
        for child in self.root.winfo_children():
            child.destroy()
        self._device_rows.clear()
        self._apply_root_theme()
        self._build()
        self._selected_id = selected
        self._scan_hits = scan_hits
        if scan_hits:
            self._populate_scan(scan_hits)
        self.refresh_device_list()
        self._schedule_poll()

    def _build(self):
        self.shell = tk.Frame(self.root, bg=self.theme["bg"])
        self.shell.pack(fill="both", expand=True)

        header = tk.Frame(self.shell, bg=self.theme["bg"], padx=20, pady=16)
        header.pack(fill="x")

        titles = tk.Frame(header, bg=self.theme["bg"])
        titles.pack(side="left", fill="x", expand=True)
        try:
            self._logo_photo = logo_photo(self.root, self.mode, height=40)
            self.title_lbl = tk.Label(
                titles,
                image=self._logo_photo,
                bg=self.theme["bg"],
                anchor="w",
            )
        except Exception:
            self._logo_photo = None
            self.title_lbl = tk.Label(
                titles,
                text="Home Pc Hub",
                bg=self.theme["bg"],
                fg=self.theme["text"],
                font=FONTS["title"],
                anchor="w",
            )
        self.title_lbl.pack(anchor="w")
        self.sub_lbl = tk.Label(
            titles,
            text=t("app.subtitle"),
            bg=self.theme["bg"],
            fg=self.theme["text_muted"],
            font=FONTS["subtitle"],
            anchor="w",
        )
        self.sub_lbl.pack(anchor="w", pady=(2, 0))

        # Mini settings strip under the title (dropdown menus)
        self.menubar = tk.Frame(self.shell, bg=self.theme["bg"], padx=20)
        self.menubar.pack(fill="x", pady=(0, 4))
        self._menu_btns: dict[str, ttk.Button] = {}
        self._rebuild_menubar()

        # Right side: language, then theme (theme sits next to language)
        self.theme_btn = ttk.Button(
            header,
            text=self._theme_btn_label(),
            style="Ghost.TButton",
            command=self._toggle_theme,
        )
        self.theme_btn.pack(side="right")
        attach_info_icon(
            header,
            ui_help("theme"),
            bg=self.theme["bg"],
            fg=self.theme["text_muted"],
            accent=self.theme["accent"],
        ).pack(side="right", padx=(0, 8))

        self.lang_btn = ttk.Button(
            header,
            text=self._lang_btn_label(),
            style="Ghost.TButton",
            command=self._toggle_lang,
        )
        self.lang_btn.pack(side="right", padx=(0, 4))
        attach_info_icon(
            header,
            ui_help("lang"),
            bg=self.theme["bg"],
            fg=self.theme["text_muted"],
            accent=self.theme["accent"],
        ).pack(side="right", padx=(0, 8))

        # Status first (side=bottom) so the expanding body cannot cover it
        self.status_bar = tk.Frame(self.shell, bg=self.theme["status_bg"], padx=20, pady=10)
        self.status_bar.pack(fill="x", side="bottom")
        status_wrap = tk.Frame(self.status_bar, bg=self.theme["status_bg"])
        status_wrap.pack(fill="x")
        attach_info_icon(
            status_wrap,
            ui_help("status"),
            bg=self.theme["status_bg"],
            fg=self.theme["text_muted"],
            accent=self.theme["accent"],
        ).pack(side="left", padx=(0, 8))
        self.status_lbl = tk.Label(
            status_wrap,
            textvariable=self.status,
            bg=self.theme["status_bg"],
            fg=self.theme["text_muted"],
            font=FONTS["subtitle"],
            anchor="w",
        )
        self.status_lbl.pack(side="left", fill="x", expand=True)

        body = tk.Frame(self.shell, bg=self.theme["bg"], padx=20)
        body.pack(fill="both", expand=True)

        # --- Devices panel ---
        self.devices_panel = tk.Frame(
            body, bg=self.theme["surface"], highlightthickness=0
        )
        self.devices_panel.pack(fill="both", expand=True)

        devices_head = tk.Frame(self.devices_panel, bg=self.theme["surface"], padx=16, pady=12)
        devices_head.pack(fill="x")
        labeled_row(
            devices_head,
            t("devices.title"),
            ui_help("devices"),
            bg=self.theme["surface"],
            fg=self.theme["text"],
            muted=self.theme["text_muted"],
            accent=self.theme["accent"],
            font_title=FONTS["ui_bold"],
        ).pack(side="left")
        self.remove_btn = ttk.Button(
            devices_head,
            text=t("devices.remove"),
            style="Ghost.TButton",
            command=self._remove_selected,
        )
        self.remove_btn.pack(side="right")
        attach_info_icon(
            devices_head,
            ui_help("remove"),
            bg=self.theme["surface"],
            fg=self.theme["text_muted"],
            accent=self.theme["accent"],
        ).pack(side="right", padx=(0, 6))

        list_wrap = tk.Frame(self.devices_panel, bg=self.theme["surface"], padx=12, pady=12)
        list_wrap.pack(fill="both", expand=True)

        self.list_canvas = tk.Canvas(
            list_wrap,
            bg=self.theme["surface"],
            highlightthickness=0,
            bd=0,
        )
        self.list_scroll = ThemedVScrollbar(
            list_wrap, self.theme, command=self.list_canvas.yview
        )
        self.saved_frame = tk.Frame(self.list_canvas, bg=self.theme["surface"])
        self.saved_frame.bind(
            "<Configure>",
            lambda e: self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all")),
        )
        self._list_window = self.list_canvas.create_window(
            (0, 0), window=self.saved_frame, anchor="nw"
        )

        def _stretch(event):
            self.list_canvas.itemconfigure(self._list_window, width=event.width)

        self.list_canvas.bind("<Configure>", _stretch)
        self.list_canvas.configure(yscrollcommand=self.list_scroll.set)
        self.list_canvas.pack(side="left", fill="both", expand=True)
        self.list_scroll.pack(side="right", fill="y")
        self._bind_list_mousewheel(self.list_canvas)

        # --- Scan panel ---
        self.scan_panel = tk.Frame(body, bg=self.theme["surface"])
        self.scan_panel.pack(fill="both", expand=True, pady=(14, 0))

        scan_head = tk.Frame(self.scan_panel, bg=self.theme["surface"], padx=16, pady=12)
        scan_head.pack(fill="x")
        labeled_row(
            scan_head,
            t("scan.title"),
            ui_help("scan"),
            bg=self.theme["surface"],
            fg=self.theme["text"],
            muted=self.theme["text_muted"],
            accent=self.theme["accent"],
            font_title=FONTS["ui_bold"],
        ).pack(side="left")

        scan_body = tk.Frame(self.scan_panel, bg=self.theme["surface"], padx=12, pady=12)
        scan_body.pack(fill="both", expand=True)

        # Buttons first (side=bottom) so Treeview expand cannot hide them
        scan_btns = tk.Frame(scan_body, bg=self.theme["surface"])
        scan_btns.pack(side="bottom", fill="x", pady=(10, 0))
        ttk.Button(
            scan_btns, text=t("scan.btn"), style="Accent.TButton", command=self._start_scan
        ).pack(side="left")
        attach_info_icon(
            scan_btns,
            ui_help("scan_btn"),
            bg=self.theme["surface"],
            fg=self.theme["text_muted"],
            accent=self.theme["accent"],
        ).pack(side="left", padx=(6, 12))
        ttk.Button(
            scan_btns, text=t("scan.add"), style="TButton", command=self._add_selected
        ).pack(side="left")
        attach_info_icon(
            scan_btns,
            ui_help("add_btn"),
            bg=self.theme["surface"],
            fg=self.theme["text_muted"],
            accent=self.theme["accent"],
        ).pack(side="left", padx=(6, 0))

        tree_wrap = tk.Frame(
            scan_body,
            bg=self.theme["border"],
            highlightthickness=0,
            bd=0,
        )
        tree_wrap.pack(fill="both", expand=True)
        tree_inner = tk.Frame(tree_wrap, bg=self.theme["surface"], padx=1, pady=1)
        tree_inner.pack(fill="both", expand=True)
        self.scan_tree = ttk.Treeview(
            tree_inner,
            columns=("alias", "model", "host", "kind", "sockets"),
            show="headings",
            height=5,
            selectmode="extended",
        )
        for col, label_key, width in (
            ("alias", "scan.col.alias", 150),
            ("model", "scan.col.model", 90),
            ("host", "scan.col.host", 120),
            ("kind", "scan.col.kind", 70),
            ("sockets", "scan.col.sockets", 55),
        ):
            self.scan_tree.heading(col, text=t(label_key))
            self.scan_tree.column(col, width=width, stretch=True)
        self.scan_tree.pack(fill="both", expand=True)

        # ensure nested panel frames use surface bg
        for panel in (self.devices_panel, self.scan_panel):
            for child in panel.winfo_children():
                try:
                    child.configure(bg=self.theme["surface"])
                except tk.TclError:
                    pass
                for sub in child.winfo_children():
                    try:
                        if not isinstance(sub, (ttk.Widget, ttk.Treeview)):
                            sub.configure(bg=self.theme["surface"])
                    except tk.TclError:
                        pass

    def _has_bulb(self) -> bool:
        for d in load_config().get("devices") or []:
            if d.get("kind") == "bulb" or d.get("has_light"):
                return True
        return False

    def _rebuild_menubar(self) -> None:
        if not hasattr(self, "menubar") or not self.menubar.winfo_exists():
            return
        for child in self.menubar.winfo_children():
            child.destroy()
        self._menu_btns.clear()
        hotkey_btn = ttk.Button(
            self.menubar,
            text=t("menu.hotkeys"),
            style="Ghost.TButton",
            command=lambda: open_hotkey_panel(self.root, self.mode),
        )
        hotkey_btn.pack(side="left")
        self._menu_btns["hotkeys"] = hotkey_btn
        if self._has_bulb():
            btn = ttk.Button(
                self.menubar,
                text=f"{t('menu.bulb')} ▾",
                style="Ghost.TButton",
                command=self._open_bulb_menu,
            )
            btn.pack(side="left", padx=(8, 0))
            self._menu_btns["bulb"] = btn

    def _open_bulb_menu(self) -> None:
        btn = self._menu_btns.get("bulb")
        menu = tk.Menu(
            self.root,
            tearoff=0,
            bg=self.theme["surface_2"],
            fg=self.theme["text"],
            activebackground=self.theme["accent"],
            activeforeground=self.theme["accent_text"],
            bd=0,
            font=FONTS["ui"],
        )
        menu.add_command(
            label=t("menu.edit_presets"),
            command=lambda: open_preset_editor(self.root, self.mode),
        )
        if btn is not None:
            try:
                x = btn.winfo_rootx()
                y = btn.winfo_rooty() + btn.winfo_height()
            except tk.TclError:
                x = self.root.winfo_pointerx()
                y = self.root.winfo_pointery()
        else:
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _theme_btn_label(self) -> str:
        return t("theme.to_light") if self.mode == "dark" else t("theme.to_dark")

    def _lang_btn_label(self) -> str:
        # Button shows the language you can switch TO
        return t("lang.to_en") if get_lang() == "tr" else t("lang.to_tr")

    def _toggle_theme(self):
        self.mode = "light" if self.mode == "dark" else "dark"
        set_theme(self.mode)
        self._rebuild_ui()

    def _toggle_lang(self):
        set_lang("en" if get_lang() == "tr" else "tr")
        self._rebuild_ui()

    def _on_list_mousewheel(self, event):
        if event.delta:
            self.list_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _bind_list_mousewheel(self, widget):
        widget.bind("<MouseWheel>", self._on_list_mousewheel)
        for child in widget.winfo_children():
            self._bind_list_mousewheel(child)

    def _sync_list_scroll(self):
        self.saved_frame.update_idletasks()
        bbox = self.list_canvas.bbox("all")
        if bbox:
            self.list_canvas.configure(scrollregion=bbox)

    def _toggle_expand(self, device_id: str):
        if device_id in self._expanded_ids:
            self._expanded_ids.discard(device_id)
        else:
            self._expanded_ids.add(device_id)
        self.refresh_device_list()

    def refresh_device_list(self):
        for child in self.saved_frame.winfo_children():
            child.destroy()
        self._device_rows.clear()

        devices = load_config()["devices"]
        self._rebuild_menubar()
        if not devices:
            empty = tk.Label(
                self.saved_frame,
                text=t("devices.empty"),
                bg=self.theme["surface"],
                fg=self.theme["text_muted"],
                font=FONTS["subtitle"],
                anchor="w",
                pady=8,
            )
            empty.pack(fill="x", padx=4)
            self._bind_list_mousewheel(self.saved_frame)
            self._sync_list_scroll()
            return

        for device in devices:
            selected = self._selected_id == device["id"]
            card = DeviceCard(
                self.saved_frame,
                self.theme,
                selected=selected,
                on_click=lambda did=device["id"]: self._select_device(did),
            )
            card.pack(fill="x", pady=5, padx=2)
            inner = card.inner

            header = tk.Frame(inner, bg=self.theme["surface_2"])
            header.pack(fill="x")

            socket_count = int(device.get("socket_count") or 0)
            kind = device.get("kind") or "other"
            is_multi = kind == "strip" or socket_count > 0
            expanded = device["id"] in self._expanded_ids

            if is_multi:
                ttk.Button(
                    header,
                    text="▾" if expanded else "▸",
                    style="Ghost.TButton",
                    width=2,
                    command=lambda did=device["id"]: self._toggle_expand(did),
                ).pack(side="left", padx=(0, 6))

            left = tk.Frame(header, bg=self.theme["surface_2"])
            left.pack(side="left", fill="x", expand=True)

            label = device.get("alias") or device["host"]
            name_lbl = tk.Label(
                left,
                text=label,
                bg=self.theme["surface_2"],
                fg=self.theme["text"],
                font=FONTS["ui_bold"],
                anchor="w",
            )
            name_lbl.pack(anchor="w")

            if is_multi:
                meta = t(
                    "meta.sockets",
                    model=device.get("model") or "—",
                    host=device["host"],
                    count=socket_count,
                )
            else:
                meta = t(
                    "meta.plain",
                    model=device.get("model") or "—",
                    host=device["host"],
                )

            meta_lbl = tk.Label(
                left,
                text=meta,
                bg=self.theme["surface_2"],
                fg=self.theme["text_muted"],
                font=FONTS["meta"],
                anchor="w",
            )
            meta_lbl.pack(anchor="w", pady=(2, 0))

            right = tk.Frame(header, bg=self.theme["surface_2"])
            right.pack(side="right")

            status_lbl = tk.Label(
                right,
                text="…",
                bg=self.theme["surface_2"],
                fg=self.theme["accent"],
                font=FONTS["subtitle"],
                width=10,
                anchor="e",
            )
            status_lbl.pack(side="left", padx=(0, 10))

            socket_switches: dict[int, ToggleSwitch] = {}
            socket_labels: dict[int, tk.Label] = {}
            device_switch = None

            if is_multi:
                # Parent-level features (LED etc.) — energy is usually per socket
                ttk.Button(
                    right,
                    text="···",
                    style="Ghost.TButton",
                    width=3,
                    command=lambda d=device: open_plug_panel(
                        self.root,
                        d,
                        self.mode,
                        socket=None,
                        on_close=lambda **_: self.refresh_device_list(),
                    ),
                ).pack(side="right")

                sockets = device.get("sockets") or [
                    {"index": i, "alias": t("status.socket_n", n=i + 1)}
                    for i in range(socket_count)
                ]
                sockets_frame = tk.Frame(inner, bg=self.theme["surface_2"])
                if expanded:
                    sockets_frame.pack(fill="x", pady=(10, 0))

                for sock in sockets:
                    idx = int(sock["index"])
                    srow = tk.Frame(sockets_frame, bg=self.theme["surface_2"])
                    srow.pack(fill="x", pady=3)

                    slbl = tk.Label(
                        srow,
                        text=sock.get("alias") or t("status.socket_n", n=idx + 1),
                        bg=self.theme["surface_2"],
                        fg=self.theme["text"],
                        font=FONTS["ui"],
                        anchor="w",
                    )
                    slbl.pack(side="left")

                    sstatus = tk.Label(
                        srow,
                        text="…",
                        bg=self.theme["surface_2"],
                        fg=self.theme["text_muted"],
                        font=FONTS["subtitle"],
                        width=8,
                        anchor="e",
                    )
                    sstatus.pack(side="left", padx=8)

                    def on_sock_toggle(on, host=device["host"], sid=device["id"], s=idx):
                        self._set_power_async(host, on, sid, socket=s)

                    switch = ToggleSwitch(
                        srow, self.theme, on_toggle=on_sock_toggle, state=False
                    )
                    switch._bg = self.theme["surface_2"]
                    switch.configure(bg=self.theme["surface_2"])
                    switch.pack(side="right")

                    ttk.Button(
                        srow,
                        text="···",
                        style="Ghost.TButton",
                        width=3,
                        command=lambda d=device, s=idx: open_plug_panel(
                            self.root,
                            d,
                            self.mode,
                            socket=s,
                            on_close=lambda **_: self.refresh_device_list(),
                        ),
                    ).pack(side="right", padx=(0, 8))

                    socket_switches[idx] = switch
                    socket_labels[idx] = sstatus
            else:

                def on_toggle(on, host=device["host"], sid=device["id"]):
                    self._set_power_async(host, on, sid)

                device_switch = ToggleSwitch(
                    right, self.theme, on_toggle=on_toggle, state=False
                )
                device_switch._bg = self.theme["surface_2"]
                device_switch.configure(bg=self.theme["surface_2"])
                device_switch.pack(side="right")

                is_bulb = (
                    kind == "bulb"
                    or device.get("has_light")
                    or bool(device.get("light_features"))
                )
                if is_bulb:
                    more = ttk.Button(
                        right,
                        text="···",
                        style="Ghost.TButton",
                        width=3,
                        command=lambda d=device: open_bulb_panel(
                            self.root,
                            d,
                            self.mode,
                            on_close=lambda **_: self.refresh_device_list(),
                        ),
                    )
                    more.pack(side="right", padx=(0, 8))
                else:
                    ttk.Button(
                        right,
                        text="···",
                        style="Ghost.TButton",
                        width=3,
                        command=lambda d=device: open_plug_panel(
                            self.root,
                            d,
                            self.mode,
                            socket=None,
                            on_close=lambda **_: self.refresh_device_list(),
                        ),
                    ).pack(side="right", padx=(0, 8))

            # click-through for selection on labels
            for w in (name_lbl, meta_lbl, left, header, inner):
                w.bind("<Button-1>", lambda e, did=device["id"]: self._select_device(did))

            self._device_rows[device["id"]] = {
                "device": device,
                "card": card,
                "switch": device_switch,
                "status": status_lbl,
                "socket_switches": socket_switches,
                "socket_labels": socket_labels,
            }

        self._bind_list_mousewheel(self.saved_frame)
        self._sync_list_scroll()
        self._refresh_states_async()

    def _select_device(self, device_id: str):
        self._selected_id = device_id
        for did, row in self._device_rows.items():
            row["card"].set_selected(did == device_id)

    def _set_status(self, text: str):
        self.status.set(text)

    def _start_scan(self):
        self._set_status(t("status.scanning"))
        for item in self.scan_tree.get_children():
            self.scan_tree.delete(item)

        def worker():
            try:
                found = scan()
                assigned = {d["host"] for d in load_config()["devices"]}
                found = [d for d in found if d["host"] not in assigned]
                self.root.after(0, lambda: self._populate_scan(found))
            except Exception as exc:
                self.root.after(0, lambda: self._set_status(t("status.scan_error", error=exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _populate_scan(self, found: list[dict]):
        self._scan_hits = found
        for d in found:
            count = d.get("socket_count") or 0
            self.scan_tree.insert(
                "",
                "end",
                iid=d["host"],
                values=(
                    d.get("alias") or "-",
                    d.get("model") or "-",
                    d["host"],
                    kind_label(d.get("kind")),
                    count if count else "-",
                ),
            )
        self._set_status(t("status.found", count=len(found)))

    def _add_selected(self):
        selected = self.scan_tree.selection()
        if not selected:
            messagebox.showinfo("Home Pc Hub", t("dialog.select_add"))
            return
        by_host = {d["host"]: d for d in self._scan_hits}
        added_hosts: list[str] = []
        for item in selected:
            hit = by_host.get(item)
            if hit is None:
                alias, model, host, kind_disp, _sockets = self.scan_tree.item(
                    item, "values"
                )
                kind_map = {kind_label(k): k for k in ("plug", "bulb", "strip", "other")}
                kind = kind_map.get(kind_disp, kind_disp if kind_disp != "-" else "other")
                hit = {
                    "host": host,
                    "alias": None if alias == "-" else alias,
                    "model": None if model == "-" else model,
                    "kind": kind,
                    "socket_count": 0,
                    "sockets": [],
                }
            try:
                add_device(
                    host=hit["host"],
                    alias=hit.get("alias"),
                    model=hit.get("model"),
                    kind=hit.get("kind") or "other",
                    socket_count=hit.get("socket_count") or 0,
                    sockets=hit.get("sockets") or [],
                    has_light=bool(hit.get("has_light") or hit.get("kind") == "bulb"),
                    light_features=hit.get("light_features"),
                )
                added_hosts.append(hit["host"])
            except ValueError as exc:
                messagebox.showwarning("Home Pc Hub", str(exc))

        for host in added_hosts:
            if self.scan_tree.exists(host):
                self.scan_tree.delete(host)
        added_set = set(added_hosts)
        self._scan_hits = [d for d in self._scan_hits if d["host"] not in added_set]

        self.refresh_device_list()
        left = len(self._scan_hits)
        if left:
            self._set_status(
                t("status.added_left", count=len(added_hosts), left=left)
            )
        else:
            self._set_status(t("status.added", count=len(added_hosts)))

    def _remove_selected(self):
        if not self._selected_id:
            messagebox.showinfo("Home Pc Hub", t("dialog.select_remove"))
            return
        device = next(
            (d for d in load_config()["devices"] if d["id"] == self._selected_id),
            None,
        )
        remove_device(self._selected_id)
        if device:
            drop_cache(device["host"])
        self._selected_id = None
        self.refresh_device_list()
        self._set_status(t("status.removed"))

    def _set_power_async(
        self, host: str, on: bool, device_id: str, socket: int | None = None
    ):
        self._set_status(t("status.sending"))
        self._inflight += 1

        def worker():
            try:
                set_power(host, on, socket=socket)

                def ok():
                    row = self._device_rows.get(device_id)
                    if row:
                        if socket is None:
                            if row["switch"] is not None:
                                row["switch"].set_state(on)
                            row["status"].configure(
                                text=t("status.on") if on else t("status.off"),
                                fg=self.theme["success"] if on else self.theme["text_muted"],
                            )
                        else:
                            sw = row["socket_switches"].get(socket)
                            lbl = row["socket_labels"].get(socket)
                            if sw:
                                sw.set_state(on)
                            if lbl:
                                lbl.configure(
                                    text=t("status.on") if on else t("status.off"),
                                    fg=self.theme["success"]
                                    if on
                                    else self.theme["text_muted"],
                                )
                            self._update_strip_summary(row)
                    self._set_status(t("status.ready"))

                self.root.after(0, ok)
            except Exception as exc:

                def fail(err=exc):
                    self._set_status(t("status.error", error=err))
                    self._refresh_states_async()

                self.root.after(0, fail)
            finally:
                def done():
                    self._inflight = max(0, self._inflight - 1)

                self.root.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _update_strip_summary(self, row: dict):
        ons = [sw.var.get() for sw in row["socket_switches"].values()]
        if not ons:
            return
        on_count = sum(1 for x in ons if x)
        row["status"].configure(
            text=t("status.strip_summary", on=on_count, total=len(ons)),
            fg=self.theme["accent"],
        )

    def _refresh_states_async(self):
        if self._refreshing or self._inflight > 0:
            return
        rows = dict(self._device_rows)
        if not rows:
            return
        self._refreshing = True
        hosts = {did: row["device"]["host"] for did, row in rows.items()}

        def worker():
            try:
                by_host = get_statuses(list(dict.fromkeys(hosts.values())))
                updates = {}
                for did, host in hosts.items():
                    data = by_host.get(host)
                    updates[did] = ("ok", data) if data is not None else ("err", None)
            except Exception:
                updates = {did: ("err", None) for did in hosts}

            def apply():
                self._refreshing = False
                if self.root.winfo_exists():
                    self._apply_state_updates(updates)

            self.root.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def _cancel_poll(self):
        if self._poll_after is not None:
            try:
                self.root.after_cancel(self._poll_after)
            except (tk.TclError, ValueError):
                pass
            self._poll_after = None

    def _schedule_poll(self):
        self._cancel_poll()
        self._poll_after = self.root.after(STATUS_POLL_MS, self._poll_states)

    def _poll_states(self):
        self._poll_after = None
        if not self.root.winfo_exists():
            return
        self._refresh_states_async()
        self._schedule_poll()

    def _apply_state_updates(self, updates: dict):
        cfg = load_config()
        changed = False

        for did, (status, data) in updates.items():
            row = self._device_rows.get(did)
            if not row:
                continue
            if status != "ok" or data is None:
                row["status"].configure(text=t("status.offline"), fg=self.theme["danger"])
                for lbl in row["socket_labels"].values():
                    lbl.configure(text="—", fg=self.theme["text_muted"])
                continue

            sockets = data.get("sockets") or []
            if sockets:
                device = row["device"]
                new_sockets = merge_sockets(device.get("sockets"), sockets)
                if (
                    device.get("socket_count") != len(sockets)
                    or socket_identity(device.get("sockets"))
                    != socket_identity(new_sockets)
                ):
                    for d in cfg["devices"]:
                        if d["id"] == did:
                            # merge against config copy too (source of truth for schedules)
                            d["sockets"] = merge_sockets(d.get("sockets"), sockets)
                            d["socket_count"] = len(sockets)
                            d["kind"] = "strip"
                            device["sockets"] = list(d["sockets"])
                            device["socket_count"] = len(sockets)
                            changed = True
                            break

                if len(row["socket_switches"]) != len(sockets):
                    if changed:
                        save_config(cfg)
                    self.refresh_device_list()
                    return

                for s in sockets:
                    idx = s["index"]
                    sw = row["socket_switches"].get(idx)
                    lbl = row["socket_labels"].get(idx)
                    if sw:
                        sw.set_state(bool(s["is_on"]))
                    if lbl:
                        lbl.configure(
                            text=t("status.on") if s["is_on"] else t("status.off"),
                            fg=self.theme["success"]
                            if s["is_on"]
                            else self.theme["text_muted"],
                        )
                self._update_strip_summary(row)
            else:
                on = bool(data.get("is_on"))
                if row["switch"] is not None:
                    row["switch"].set_state(on)
                row["status"].configure(
                    text=t("status.on") if on else t("status.off"),
                    fg=self.theme["success"] if on else self.theme["text_muted"],
                )

        if changed:
            save_config(cfg)
