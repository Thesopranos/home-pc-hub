"""Circadian ambient — Kelvin/brightness follow local time of day."""

from __future__ import annotations

import threading
import time

from homepchub.core.devices import set_light_brightness, set_light_color_temp, set_power
from homepchub.core.presets.base import register

# (hour, kelvin, brightness) — same curve as Home Hub
KEYFRAMES = [
    (0, 2500, 5),
    (6, 2500, 15),
    (8, 5000, 70),
    (12, 6500, 100),
    (15, 6000, 90),
    (18, 4000, 60),
    (20, 2700, 30),
    (22, 2500, 12),
    (24, 2500, 5),
]
REFRESH_S = 5 * 60

_stops: dict[str, threading.Event] = {}
_threads: dict[str, threading.Thread] = {}


def _for_hour(hour: float) -> tuple[int, int]:
    for (h0, k0, b0), (h1, k1, b1) in zip(KEYFRAMES, KEYFRAMES[1:]):
        if h0 <= hour <= h1:
            frac = (hour - h0) / (h1 - h0) if h1 != h0 else 0
            return round(k0 + (k1 - k0) * frac), round(b0 + (b1 - b0) * frac)
    return KEYFRAMES[-1][1], KEYFRAMES[-1][2]


def _loop(host: str, stop: threading.Event) -> None:
    last = None
    set_power(host, True, socket=None)
    while not stop.is_set():
        now = time.localtime()
        hour = now.tm_hour + now.tm_min / 60
        kelvin, brightness = _for_hour(hour)
        if (kelvin, brightness) != last:
            try:
                set_light_color_temp(host, kelvin, brightness=brightness)
            except Exception:
                try:
                    set_light_brightness(host, brightness)
                except Exception:
                    pass
            last = (kelvin, brightness)
        stop.wait(REFRESH_S)


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


register("circadian", label_key="preset.circadian", apply=_apply, stop=_stop)
