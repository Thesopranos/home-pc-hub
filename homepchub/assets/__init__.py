"""Resolved paths and helpers for packaged brand assets."""

from __future__ import annotations

import json
import sys
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageTk

_ASSETS = Path(__file__).resolve().parent


def path(*parts: str) -> Path:
    return _ASSETS.joinpath(*parts)


def brand_meta() -> dict:
    try:
        return json.loads(path("brand.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_image(*parts: str) -> Image.Image:
    return Image.open(path(*parts)).convert("RGBA")


def tray_image(*, dark_taskbar: bool = True) -> Image.Image:
    """Windows taskbars are typically dark → white glyph; light → black glyph."""
    name = "tray-white-32.png" if dark_taskbar else "tray-black-32.png"
    return load_image("tray", name)


def logo_image(mode: str, *, height: int = 36) -> Image.Image:
    """Horizontal logo without tagline, sized for headers."""
    name = "logo-dark.png" if mode == "dark" else "logo-light.png"
    img = load_image("logo", name)
    if img.height != height:
        w = max(1, round(img.width * (height / img.height)))
        img = img.resize((w, height), Image.Resampling.LANCZOS)
    return img


def logo_photo(master: tk.Misc, mode: str, *, height: int = 36) -> ImageTk.PhotoImage:
    return ImageTk.PhotoImage(logo_image(mode, height=height), master=master)


def apply_window_icons(root: tk.Misc) -> None:
    """Set taskbar / title-bar icons from brand pack (never leave the Tk feather)."""
    photos: list[ImageTk.PhotoImage] = []
    try:
        for size in (16, 32, 48, 64):
            p = path("app-icon", f"icon-{size}.png")
            if p.is_file():
                photos.append(ImageTk.PhotoImage(Image.open(p), master=root))
        if photos:
            # This window + default for later Toplevels spawned from it.
            root.iconphoto(False, *photos)
            root.iconphoto(True, *photos)
            root._brand_icon_photos = photos  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        ico = path("app-icon", "icon.ico")
        if sys.platform == "win32" and ico.is_file():
            root.iconbitmap(str(ico))
    except Exception:
        pass
