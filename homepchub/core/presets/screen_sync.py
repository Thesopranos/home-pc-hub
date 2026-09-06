"""Screen sync ambient - match average color of a chosen monitor."""

from __future__ import annotations

import colorsys
import threading

from PIL import Image, ImageGrab

from homepchub.core.config import get_screen_sync_boost, get_screen_sync_monitor
from homepchub.core.devices import set_light_hsv, set_power
from homepchub.core.monitors import list_monitors
from homepchub.core.presets.base import register

POLL_S = 1
_stops: dict[str, threading.Event] = {}
_threads: dict[str, threading.Thread] = {}


def _sync_bbox() -> tuple[int, int, int, int] | None:
    monitors = list_monitors()
    index = get_screen_sync_monitor()
    if 0 <= index < len(monitors):
        return monitors[index]
    return None


def _loop(host: str, stop: threading.Event) -> None:
    last = None
    set_power(host, True, socket=None)
    while not stop.is_set():
        try:
            bbox = _sync_bbox()
            grab_kw = {"bbox": bbox} if bbox else {}
            img = ImageGrab.grab(**grab_kw).convert("RGB").resize(
                (1, 1), Image.Resampling.LANCZOS
            )
            r, g, b = img.getpixel((0, 0))
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            hue, sat = h * 360, s * 100
            brightness = max(get_screen_sync_boost(), round(v * 100))
            hsv = (int(hue), int(sat), int(brightness))
            if hsv != last:
                set_light_hsv(host, hsv[0], hsv[1], value=hsv[2])
                last = hsv
        except Exception:
            pass
        stop.wait(POLL_S)


def _apply(host: str) -> None:
    _stop(host)
    stop = threading.Event()
    _stops[host] = stop
    th = threading.Thread(target=_loop, args=(host, stop), daemon=True)
    _threads[host] = th
    th.start()


def _stop(host: str) -> None:
    stop = _stops.pop(host, None)
    if stop:
        stop.set()
    _threads.pop(host, None)


register("screen_sync", label_key="preset.screen_sync", apply=_apply, stop=_stop)
