"""UI theme tokens for Home Pc Hub — aligned with brand.json palette."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

FONTS = {
    "ui": ("Bahnschrift", 11),
    "ui_bold": ("Bahnschrift", 11, "bold"),
    "title": ("Bahnschrift", 18, "bold"),
    "subtitle": ("Bahnschrift", 10),
    "meta": ("Cascadia Mono", 9),
    "button": ("Bahnschrift", 10),
}

# Brand: primary #1FA98C, night #0B1A17, paper #F2F5F4, ink #16211F
THEMES = {
    "dark": {
        "bg": "#0B1A17",
        "surface": "#122622",
        "surface_2": "#1A3330",
        "border": "#2A4540",
        "border_strong": "#3A5A54",
        "text": "#E8F2EF",
        "text_muted": "#8AA39C",
        "accent": "#1FA98C",
        "accent_text": "#06201A",
        "accent_dim": "#164A40",
        "success": "#6BCB8F",
        "danger": "#E07A6A",
        "track_off": "#2A4540",
        "knob": "#F4F6FA",
        "select_bg": "#1F3D38",
        "row_alt": "#0F201C",
        "status_bg": "#071412",
    },
    "light": {
        "bg": "#F2F5F4",
        "surface": "#FFFFFF",
        "surface_2": "#C8D4CF",
        "border": "#A8B8B2",
        "border_strong": "#8A9E97",
        "text": "#16211F",
        "text_muted": "#5C6F6A",
        "accent": "#0E6B58",
        "accent_text": "#F2F5F4",
        "accent_dim": "#D4EFE8",
        "success": "#2F9E5F",
        "danger": "#C45C4C",
        "track_off": "#A8B8B2",
        "knob": "#FFFFFF",
        "select_bg": "#D4EFE8",
        "row_alt": "#F7FAF9",
        "status_bg": "#D5DFDB",
    },
}


def get_theme(mode: str) -> dict:
    return THEMES.get(mode, THEMES["dark"])


def apply_ttk(style: ttk.Style, theme: dict) -> None:
    # Re-selecting clam every time flashes default colors (theme flicker).
    try:
        if style.theme_use() != "clam":
            style.theme_use("clam")
    except tk.TclError:
        style.theme_use("clam")

    style.configure(".", background=theme["bg"], foreground=theme["text"], font=FONTS["ui"])
    style.configure("TFrame", background=theme["bg"])
    style.configure("Surface.TFrame", background=theme["surface"])
    style.configure("Card.TFrame", background=theme["surface_2"])
    style.configure(
        "TLabel",
        background=theme["bg"],
        foreground=theme["text"],
        font=FONTS["ui"],
    )
    style.configure(
        "Surface.TLabel",
        background=theme["surface"],
        foreground=theme["text"],
        font=FONTS["ui"],
    )
    style.configure(
        "Muted.TLabel",
        background=theme["bg"],
        foreground=theme["text_muted"],
        font=FONTS["subtitle"],
    )
    style.configure(
        "Card.TLabel",
        background=theme["surface_2"],
        foreground=theme["text"],
        font=FONTS["ui"],
    )
    style.configure(
        "CardMuted.TLabel",
        background=theme["surface_2"],
        foreground=theme["text_muted"],
        font=FONTS["subtitle"],
    )
    style.configure(
        "Title.TLabel",
        background=theme["bg"],
        foreground=theme["text"],
        font=FONTS["title"],
    )
    style.configure(
        "Accent.TLabel",
        background=theme["surface_2"],
        foreground=theme["accent"],
        font=FONTS["meta"],
    )
    style.configure(
        "Status.TLabel",
        background=theme["status_bg"],
        foreground=theme["text_muted"],
        font=FONTS["subtitle"],
    )

    style.configure(
        "TButton",
        background=theme["surface_2"],
        foreground=theme["text"],
        borderwidth=0,
        focuscolor=theme["accent"],
        font=FONTS["button"],
        padding=(14, 8),
    )
    style.map(
        "TButton",
        background=[("active", theme["border"]), ("pressed", theme["border_strong"])],
        foreground=[("disabled", theme["text_muted"])],
    )
    style.configure(
        "Accent.TButton",
        background=theme["accent"],
        foreground=theme["accent_text"],
        borderwidth=0,
        font=FONTS["button"],
        padding=(14, 8),
    )
    style.map(
        "Accent.TButton",
        background=[("active", theme["accent"]), ("pressed", theme["accent"])],
    )
    style.configure(
        "Ghost.TButton",
        background=theme["bg"],
        foreground=theme["text_muted"],
        borderwidth=0,
        font=FONTS["button"],
        padding=(10, 6),
    )
    style.map(
        "Ghost.TButton",
        background=[("active", theme["surface_2"])],
        foreground=[("active", theme["text"])],
    )

    style.configure(
        "Treeview",
        background=theme["surface"],
        fieldbackground=theme["surface"],
        foreground=theme["text"],
        borderwidth=1,
        relief="flat",
        bordercolor=theme["border"],
        lightcolor=theme["border"],
        darkcolor=theme["border"],
        rowheight=28,
        font=FONTS["ui"],
    )
    style.configure(
        "Treeview.Heading",
        background=theme["surface_2"],
        foreground=theme["text_muted"],
        borderwidth=0,
        relief="flat",
        bordercolor=theme["border"],
        lightcolor=theme["border"],
        darkcolor=theme["border"],
        font=FONTS["subtitle"],
    )
    style.map(
        "Treeview",
        background=[("selected", theme["select_bg"])],
        foreground=[("selected", theme["text"])],
        bordercolor=[("focus", theme["border"]), ("!focus", theme["border"])],
        lightcolor=[("focus", theme["border"]), ("!focus", theme["border"])],
        darkcolor=[("focus", theme["border"]), ("!focus", theme["border"])],
    )
    style.map(
        "Treeview.Heading",
        background=[("active", theme["border"])],
        relief=[("active", "flat")],
    )
    # clam Treeview draws a harsh system border; keep only the tree area
    try:
        style.layout(
            "Treeview",
            [("Treeview.treearea", {"sticky": "nswe"})],
        )
    except tk.TclError:
        pass

    for sb_style in ("TScrollbar", "Vertical.TScrollbar", "Horizontal.TScrollbar"):
        style.configure(
            sb_style,
            background=theme["surface_2"],
            troughcolor=theme["surface"],
            bordercolor=theme["surface"],
            lightcolor=theme["surface_2"],
            darkcolor=theme["surface_2"],
            arrowcolor=theme["text_muted"],
            relief="flat",
            borderwidth=0,
            gripcount=0,
            arrowsize=12,
        )
        style.map(
            sb_style,
            background=[
                ("pressed", theme["border_strong"]),
                ("active", theme["border"]),
                ("!disabled", theme["surface_2"]),
            ],
            arrowcolor=[
                ("disabled", theme["border"]),
                ("pressed", theme["text"]),
                ("active", theme["text"]),
                ("!disabled", theme["text_muted"]),
            ],
            relief=[("pressed", "flat"), ("active", "flat"), ("!disabled", "flat")],
        )

    style.configure(
        "TEntry",
        fieldbackground=theme["surface_2"],
        foreground=theme["text"],
        insertcolor=theme["text"],
        bordercolor=theme["border"],
        lightcolor=theme["border"],
        darkcolor=theme["border"],
        padding=8,
    )
    style.map(
        "TEntry",
        fieldbackground=[("disabled", theme["surface"])],
        foreground=[("disabled", theme["text_muted"])],
    )

    style.configure(
        "TCombobox",
        fieldbackground=theme["surface_2"],
        background=theme["surface_2"],
        foreground=theme["text"],
        arrowcolor=theme["text"],
        bordercolor=theme["border"],
        lightcolor=theme["border"],
        darkcolor=theme["border"],
        insertcolor=theme["text"],
        selectbackground=theme["select_bg"],
        selectforeground=theme["text"],
        padding=6,
    )
    style.map(
        "TCombobox",
        fieldbackground=[
            ("readonly", theme["surface_2"]),
            ("disabled", theme["surface"]),
        ],
        foreground=[
            ("readonly", theme["text"]),
            ("disabled", theme["text_muted"]),
        ],
        background=[
            ("readonly", theme["surface_2"]),
            ("active", theme["border"]),
        ],
        arrowcolor=[("disabled", theme["text_muted"])],
        selectbackground=[("readonly", theme["select_bg"])],
        selectforeground=[("readonly", theme["text"])],
    )

    # Dropdown list (popdown) — not covered by TCombobox alone
    master = getattr(style, "master", None)
    if master is not None:
        master.option_add("*TCombobox*Listbox.background", theme["surface_2"])
        master.option_add("*TCombobox*Listbox.foreground", theme["text"])
        master.option_add("*TCombobox*Listbox.selectBackground", theme["accent"])
        master.option_add("*TCombobox*Listbox.selectForeground", theme["accent_text"])
        master.option_add("*TCombobox*Listbox.font", FONTS["ui"])

    style.configure(
        "TNotebook",
        background=theme["bg"],
        borderwidth=1,
        relief="flat",
        bordercolor=theme["border"],
        lightcolor=theme["border"],
        darkcolor=theme["border"],
        tabmargins=(0, 0, 0, 0),
    )
    style.map(
        "TNotebook",
        background=[("!selected", theme["bg"])],
        bordercolor=[("!selected", theme["border"]), ("selected", theme["border"])],
        lightcolor=[("!selected", theme["border"]), ("selected", theme["border"])],
        darkcolor=[("!selected", theme["border"]), ("selected", theme["border"])],
    )
    style.configure(
        "TNotebook.Tab",
        background=theme["surface_2"],
        foreground=theme["text_muted"],
        borderwidth=1,
        relief="flat",
        bordercolor=theme["border"],
        lightcolor=theme["border"],
        darkcolor=theme["border"],
        focuscolor=theme["border"],
        padding=(14, 8),
        font=FONTS["button"],
    )
    style.map(
        "TNotebook.Tab",
        background=[
            ("selected", theme["bg"]),
            ("active", theme["border"]),
        ],
        foreground=[
            ("selected", theme["text"]),
            ("active", theme["text"]),
        ],
        bordercolor=[
            ("selected", theme["border"]),
            ("active", theme["border"]),
            ("!selected", theme["border"]),
        ],
        lightcolor=[
            ("selected", theme["bg"]),
            ("!selected", theme["border"]),
        ],
        darkcolor=[
            ("selected", theme["border"]),
            ("!selected", theme["border"]),
        ],
        expand=[("selected", [1, 1, 1, 0])],
    )

    style.configure(
        "TCheckbutton",
        background=theme["bg"],
        foreground=theme["text"],
        focuscolor=theme["accent"],
        font=FONTS["ui"],
    )
    style.map(
        "TCheckbutton",
        background=[("active", theme["bg"])],
        foreground=[("disabled", theme["text_muted"])],
    )
    style.configure(
        "Surface.TCheckbutton",
        background=theme["surface"],
        foreground=theme["text"],
        focuscolor=theme["accent"],
        font=FONTS["ui"],
    )
    style.map(
        "Surface.TCheckbutton",
        background=[("active", theme["surface"])],
        foreground=[("disabled", theme["text_muted"])],
    )
