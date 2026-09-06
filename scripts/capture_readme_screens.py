"""Capture README screenshots in TR and EN.

Tkinter has no built-in screenshot API — window coords + Pillow ImageGrab.
Run:  .venv\\Scripts\\python scripts\\capture_readme_screens.py
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "screenshots"
OUT.mkdir(exist_ok=True)

SHOTS = (
    "main",
    "ambient-editor",
    "schedule",
    "flyout",
)


def _grab(win: tk.Misc, path: Path, *, pad: int = 0) -> None:
    win.update_idletasks()
    win.update()
    x = int(win.winfo_rootx()) - pad
    y = int(win.winfo_rooty()) - pad
    w = int(win.winfo_width()) + pad * 2
    h = int(win.winfo_height()) + pad * 2
    if w < 50 or h < 50:
        raise RuntimeError(f"window too small for capture: {path.name} {w}x{h}")
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    img.save(path)
    print(f"saved {path.name} ({img.size[0]}x{img.size[1]})")


def _toplevels(root: tk.Tk) -> list[tk.Toplevel]:
    return [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]


def _capture_lang(lang: str) -> None:
    from homepchub.core.config import get_theme_mode, load_config
    from homepchub.core.presets import store as preset_store
    from homepchub.i18n import set_lang
    from homepchub.ui.flyout import close_flyout, open_flyout
    from homepchub.ui.preset_editor import open_preset_editor
    from homepchub.ui.schedule_panel import open_schedule_panel
    from homepchub.ui.window import MainWindow

    set_lang(lang)
    theme_mode = get_theme_mode()
    devices = load_config().get("devices") or []

    prev_actions = preset_store.get_actions("reading")
    sample = []
    for tgt in preset_store.iter_action_targets():
        if tgt["kind"] == "plug":
            sample.append(
                {
                    "device_id": tgt["device_id"],
                    "socket": tgt["socket"],
                    "action": preset_store.ACTION_OFF,
                }
            )
            break
    for tgt in preset_store.iter_action_targets():
        if tgt["kind"] == "bulb":
            sample.append(
                {
                    "device_id": tgt["device_id"],
                    "socket": None,
                    "action": preset_store.ACTION_APPLY_MODE,
                }
            )
            break
    if sample:
        preset_store.set_actions("reading", sample)

    root = tk.Tk()
    MainWindow(root)
    root.deiconify()
    root.lift()
    root.attributes("-topmost", True)
    root.after(150, lambda: root.attributes("-topmost", False))

    step = {"n": 0}
    prefix = lang

    def restore():
        preset_store.set_actions("reading", prev_actions)

    def fail(msg: str):
        restore()
        print(f"ERROR [{lang}]:", msg)
        try:
            root.destroy()
        except tk.TclError:
            pass

    def go():
        n = step["n"]
        step["n"] += 1
        try:
            if n == 0:
                _grab(root, OUT / f"{prefix}-main.png")
                open_preset_editor(root, theme_mode)
                root.after(700, go)
            elif n == 1:
                tops = _toplevels(root)
                if not tops:
                    return fail("preset editor missing")
                ed = tops[-1]
                _grab(ed, OUT / f"{prefix}-ambient-editor.png")
                ed.destroy()
                root.after(300, go)
            elif n == 2:
                if not devices:
                    print(f"skip schedule [{lang}] (no devices)")
                    root.after(100, go)
                    return
                target = devices[0]
                socket = None
                for d in devices:
                    if int(d.get("socket_count") or 0) > 0 or d.get("kind") == "strip":
                        target = d
                        socket = 0
                        break
                    if d.get("kind") != "bulb" and not d.get("has_light"):
                        target = d
                        break
                open_schedule_panel(root, target, theme_mode, socket=socket)
                root.after(700, go)
            elif n == 3:
                tops = _toplevels(root)
                if tops:
                    _grab(tops[-1], OUT / f"{prefix}-schedule.png")
                    tops[-1].destroy()
                else:
                    print(f"skip schedule capture [{lang}]")
                root.after(300, go)
            elif n == 4:
                open_flyout(root)
                root.after(800, go)
            elif n == 5:
                from homepchub.ui import flyout as flyout_mod

                fw = flyout_mod._flyout_window
                if fw is not None and fw.winfo_exists():
                    _grab(fw, OUT / f"{prefix}-flyout.png")
                    close_flyout()
                else:
                    print(f"skip flyout [{lang}]")
                restore()
                root.after(200, root.destroy)
            else:
                restore()
                root.destroy()
        except Exception as exc:
            restore()
            print(f"ERROR [{lang}]:", exc)
            try:
                root.destroy()
            except tk.TclError:
                pass

    root.after(900, go)
    root.mainloop()


def main() -> None:
    from homepchub.i18n import get_lang, set_lang

    prev = get_lang()
    try:
        for lang in ("en", "tr"):
            print(f"--- capturing {lang} ---")
            _capture_lang(lang)
    finally:
        set_lang(prev if prev in ("tr", "en") else "tr")
        # remove legacy names
        for name in (
            "ss1.png",
            "ss2.png",
            "ss3.png",
            "ss4_main_bulb_menu.png",
            "ss5_ambient_editor.png",
            "ss6_schedule.png",
            "ss7_flyout.png",
        ):
            p = OUT / name
            if p.exists():
                p.unlink()
                print(f"deleted {name}")
    print("done ->", OUT)


if __name__ == "__main__":
    main()
