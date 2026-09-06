import ctypes
import sys
import threading
import tkinter as tk

import pystray

from homepchub.assets import tray_image
from homepchub.core.config import ensure_credentials, get_theme_mode
from homepchub.core.devices import set_credentials
from homepchub.core import hotkeys as hotkey_engine
from homepchub.core import notifications as notify_engine
from homepchub.core.scheduler import start as start_scheduler
from homepchub.i18n import t
from homepchub.ui.flyout import close_flyout, open_flyout
from homepchub.ui.theme import get_theme
from homepchub.ui.window import MainWindow
from homepchub.ui.winchrome import dress_window

DOUBLE_CLICK_MS = 350
_click_state = {"after_id": None}
_MUTEX_NAME = "Local\\HomePcHub.TrayApp.SingleInstance"
_ERROR_ALREADY_EXISTS = 183


def _claim_single_instance() -> bool:
    """Only one tray process may run - shared WinRT notify API hangs otherwise."""
    try:
        handle = ctypes.windll.kernel32.CreateMutexW(None, False, _MUTEX_NAME)
        if not handle:
            return True
        if ctypes.windll.kernel32.GetLastError() == _ERROR_ALREADY_EXISTS:
            return False
        return True
    except Exception:
        return True


def main():
    if not _claim_single_instance():
        sys.exit(0)

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
        notify_engine.stop_listener()
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

    hotkey_engine.set_actions(
        on_flyout=lambda: root.after(0, confirm_single_click),
        on_settings=lambda: root.after(0, show_full),
    )
    hotkey_engine.reload()
    notify_engine.start_if_enabled()

    root.mainloop()
    _ = main_win


if __name__ == "__main__":
    main()
