import ctypes
import sys
import threading
import tkinter as tk

import pystray

from homepchub.assets import tray_image
from homepchub.core.config import ensure_credentials, get_theme_mode
from homepchub.core.devices import set_credentials
from homepchub.core.scheduler import start as start_scheduler
from homepchub.i18n import t
from homepchub.ui.flyout import close_flyout, open_flyout
from homepchub.ui.theme import get_theme
from homepchub.ui.window import MainWindow
from homepchub.ui.winchrome import dress_window

DOUBLE_CLICK_MS = 350
_click_state = {"after_id": None}


def main():
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "HomePcHub.TrayApp"
        )
    except Exception:
        pass

    creds = ensure_credentials()
    if not creds:
        sys.exit(0)

    set_credentials(creds["tapo_email"], creds["tapo_password"])
    start_scheduler()

    root = tk.Tk()
    root.withdraw()
    mode = get_theme_mode()
    dress_window(root, get_theme(mode), dark=mode == "dark")
    main_win = MainWindow(root)

    def show_full(icon=None, item=None):
        close_flyout()

        def go():
            root.deiconify()
            root.lift()
            root.focus_force()

        root.after(0, go)

    def quit_app(icon, item=None):
        close_flyout()
        icon.stop()
        root.after(0, root.destroy)

    def on_close():
        root.withdraw()

    root.protocol("WM_DELETE_WINDOW", on_close)

    def confirm_single_click():
        _click_state["after_id"] = None
        open_flyout(root, on_open_full=lambda: show_full())

    def on_tray_activate(icon=None, item=None):
        def handle():
            if _click_state["after_id"] is not None:
                root.after_cancel(_click_state["after_id"])
                _click_state["after_id"] = None
                show_full()
            else:
                _click_state["after_id"] = root.after(
                    DOUBLE_CLICK_MS, confirm_single_click
                )

        root.after(0, handle)

    icon = pystray.Icon(
        "home-pc-hub",
        tray_image(dark_taskbar=True),
        "Home Pc Hub",
        menu=pystray.Menu(
            pystray.MenuItem(
                "__click__",
                on_tray_activate,
                default=True,
                visible=False,
            ),
            pystray.MenuItem(t("tray.open"), lambda i, item: show_full()),
            pystray.MenuItem(
                t("tray.flyout"),
                lambda i, item: root.after(0, confirm_single_click),
            ),
            pystray.MenuItem(t("tray.exit"), quit_app),
        ),
    )
    threading.Thread(target=icon.run, daemon=True).start()
    root.mainloop()
    _ = main_win


if __name__ == "__main__":
    main()
