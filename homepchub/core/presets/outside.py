"""Outside ambient — color from local weather + time of day."""

from __future__ import annotations

import math
import threading
import time
import urllib.request
import json

from homepchub.core.devices import set_light_brightness, set_light_hsv, set_power
from homepchub.core.presets.base import register

GEO_API = "http://ip-api.com/json/"
WEATHER_API = "https://api.open-meteo.com/v1/forecast"
REFRESH_S = 15 * 60

_WEATHER_LOOK = [
    ({0}, (45, 15, 95, 15)),
    ({1, 2, 3}, (40, 12, 80, 12)),
    ({45, 48}, (200, 8, 50, 10)),
    ({51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}, (210, 25, 35, 8)),
    ({71, 73, 75, 77, 85, 86}, (200, 10, 85, 20)),
    ({95, 96, 99}, (250, 35, 25, 15)),
]

_stops: dict[str, threading.Event] = {}
_threads: dict[str, threading.Thread] = {}


def _time_factor(hour: float) -> float:
    return (math.cos((hour - 13) / 12 * math.pi) + 1) / 2


def _weather_to_hsv(code: int, hour: float) -> tuple[float, float, int]:
    hue, sat, day_b, night_b = next(
        (vals for codes, vals in _WEATHER_LOOK if code in codes), (210, 15, 60, 15)
    )
    brightness = round(night_b + (day_b - night_b) * _time_factor(hour))
    return hue, sat, brightness


def _fetch_hsv() -> tuple[float, float, int]:
    with urllib.request.urlopen(GEO_API, timeout=5) as r:
        geo = json.loads(r.read().decode())
    url = (
        f"{WEATHER_API}?latitude={geo['lat']}&longitude={geo['lon']}"
        "&current_weather=true"
    )
    with urllib.request.urlopen(url, timeout=5) as r:
        weather = json.loads(r.read().decode())["current_weather"]
    now = time.localtime()
    hour = now.tm_hour + now.tm_min / 60
    return _weather_to_hsv(int(weather["weathercode"]), hour)


def _loop(host: str, stop: threading.Event) -> None:
    last = None
    set_power(host, True, socket=None)
    while not stop.is_set():
        try:
            hsv = _fetch_hsv()
            if hsv != last:
                set_light_hsv(host, int(hsv[0]), int(hsv[1]), value=int(hsv[2]))
                last = hsv
        except Exception:
            pass
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


register("outside", label_key="preset.outside", apply=_apply, stop=_stop)
