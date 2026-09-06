"""Windows toast notification rules → device steps (scene-like)."""

from __future__ import annotations

import asyncio
import threading
import time
import uuid

from homepchub.core.config import load_config, save_config
from homepchub.core.presets import store as preset_store

try:
    import winsdk.windows.ui.notifications as un
    import winsdk.windows.ui.notifications.management as unm

    HAS_WINSDK = True
except ImportError:  # pragma: no cover
    un = None  # type: ignore
    unm = None  # type: ignore
    HAS_WINSDK = False

ACTION_APPLY_MODE = preset_store.ACTION_APPLY_MODE
ACTION_ON = preset_store.ACTION_ON
ACTION_OFF = preset_store.ACTION_OFF
ACTION_TOGGLE = preset_store.ACTION_TOGGLE
ACTION_WAIT = "wait"
ACTION_SET_HSV = "set_hsv"
ACTION_RESTORE = "restore"

_MAX_WAIT_MS = 600_000
_POLL_SECONDS = 0.05
_POLL_TIMEOUT = 8.0
_SEEN_CAP = 800

_stop = threading.Event()
_thread: threading.Thread | None = None
_worker: threading.Thread | None = None
_seen_ids: set[int] | None = None
_access_ok = False
_busy = threading.Lock()
_pending: list[str | None] = []
_pending_wake = threading.Event()
_run_id = 0

# Suggested app display names (Windows toast AppInfo.DisplayInfo.DisplayName)
APP_SUGGESTIONS = (
    "WhatsApp",
    "Gmail",
    "Telegram",
    "Discord",
    "Slack",
    "Outlook",
    "Microsoft Teams",
    "Chrome",
    "Microsoft Edge",
    "Spotify",
    "Signal",
)


def available() -> bool:
    return HAS_WINSDK


def _bucket(cfg: dict | None = None) -> dict:
    cfg = cfg if cfg is not None else load_config()
    bucket = cfg.get("notifications")
    if not isinstance(bucket, dict):
        bucket = {}
        cfg["notifications"] = bucket
    bucket.setdefault("enabled", False)
    bucket.setdefault("rules", [])
    return bucket


def _clean_step(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    action = raw.get("action")
    if action == ACTION_WAIT:
        try:
            ms = int(raw.get("ms", 0))
        except (TypeError, ValueError):
            return None
        return {"action": ACTION_WAIT, "ms": max(0, min(_MAX_WAIT_MS, ms))}

    device_id = raw.get("device_id")
    if not device_id:
        return None
    socket = raw.get("socket")
    if socket is not None:
        try:
            socket = int(socket)
        except (TypeError, ValueError):
            socket = None

    if action == ACTION_SET_HSV:
        try:
            hue = max(0, min(360, int(raw.get("hue", 0))))
            sat = max(0, min(100, int(raw.get("saturation", 100))))
            bri = max(1, min(100, int(raw.get("brightness", 100))))
        except (TypeError, ValueError):
            return None
        return {
            "device_id": str(device_id),
            "socket": None,
            "action": ACTION_SET_HSV,
            "hue": hue,
            "saturation": sat,
            "brightness": bri,
        }

    if action == ACTION_RESTORE:
        return {"device_id": str(device_id), "socket": socket, "action": ACTION_RESTORE}

    if action not in (ACTION_APPLY_MODE, ACTION_ON, ACTION_OFF, ACTION_TOGGLE):
        return None
    step = {
        "device_id": str(device_id),
        "socket": socket,
        "action": action,
    }
    if action == ACTION_APPLY_MODE:
        preset_id = (raw.get("preset_id") or "").strip()
        if not preset_id:
            return None
        step["preset_id"] = preset_id
    return step


def _clean_rule(raw: dict) -> dict | None:
    if not isinstance(raw, dict) or not raw.get("id"):
        return None
    apps = raw.get("apps") or []
    if isinstance(apps, str):
        apps = [a.strip() for a in apps.split(",") if a.strip()]
    else:
        apps = [str(a).strip() for a in apps if str(a).strip()]
    steps = []
    for s in raw.get("steps") or []:
        c = _clean_step(s)
        if c:
            steps.append(c)
    return {
        "id": str(raw["id"]),
        "label": (raw.get("label") or "").strip() or raw["id"],
        "enabled": bool(raw.get("enabled", True)),
        "apps": apps,
        "steps": steps,
    }


def get_settings() -> dict:
    b = _bucket()
    rules = []
    for r in b.get("rules") or []:
        c = _clean_rule(r)
        if c:
            rules.append(c)
    return {"enabled": bool(b.get("enabled")), "rules": rules}


def set_settings(*, enabled: bool, rules: list[dict]) -> None:
    cfg = load_config()
    cleaned = []
    for r in rules or []:
        c = _clean_rule(r)
        if c:
            cleaned.append(c)
    cfg["notifications"] = {"enabled": bool(enabled), "rules": cleaned}
    save_config(cfg)
    # Rules are read live from config; only flip the listener on/off.
    if enabled and HAS_WINSDK:
        start_listener()
    else:
        stop_listener()


def upsert_rule(
    *,
    rule_id: str | None,
    label: str,
    apps: list[str],
    steps: list[dict],
    enabled: bool = True,
) -> dict:
    label = (label or "").strip()
    if not label:
        raise ValueError("empty label")
    settings = get_settings()
    rules = list(settings["rules"])
    item = {
        "id": rule_id or f"notify_{uuid.uuid4().hex[:10]}",
        "label": label,
        "enabled": bool(enabled),
        "apps": apps,
        "steps": steps,
    }
    cleaned = _clean_rule(item)
    if not cleaned:
        raise ValueError("invalid rule")
    if rule_id:
        for i, r in enumerate(rules):
            if r["id"] == rule_id:
                rules[i] = cleaned
                set_settings(enabled=settings["enabled"], rules=rules)
                return cleaned
        raise KeyError(rule_id)
    rules.append(cleaned)
    set_settings(enabled=settings["enabled"], rules=rules)
    return cleaned


def delete_rule(rule_id: str) -> None:
    settings = get_settings()
    rules = [r for r in settings["rules"] if r["id"] != rule_id]
    set_settings(enabled=settings["enabled"], rules=rules)


def _app_matches(rule_apps: list[str], app_name: str | None) -> bool:
    if not rule_apps:
        return True
    name = (app_name or "").casefold()
    if not name:
        return False
    for needle in rule_apps:
        n = needle.casefold()
        if n and (n in name or name in n):
            return True
    return False


def _snapshot_host(host: str) -> dict:
    from homepchub.core.devices import get_light_state, get_power

    try:
        light = get_light_state(host)
    except Exception:
        light = {"supported": False}
    try:
        is_on = get_power(host, None)
    except Exception:
        is_on = bool(light.get("is_on"))
    return {
        "supported": bool(light.get("supported")),
        "is_on": is_on,
        "brightness": light.get("brightness"),
        "hsv": light.get("hsv"),
        "color_temp": light.get("color_temp"),
    }


def _restore_host(host: str, snap: dict) -> None:
    from homepchub.core.devices import (
        set_light_brightness,
        set_light_color_temp,
        set_light_hsv,
        set_power,
    )

    if not snap.get("is_on"):
        set_power(host, False, socket=None)
        return
    set_power(host, True, socket=None)
    if not snap.get("supported"):
        return
    hsv = snap.get("hsv")
    if isinstance(hsv, dict) and hsv.get("hue") is not None:
        set_light_hsv(
            host,
            int(hsv["hue"]),
            int(hsv.get("saturation", 100)),
            int(hsv.get("value") or snap.get("brightness") or 100),
        )
        return
    if snap.get("color_temp") is not None:
        set_light_color_temp(
            host,
            int(snap["color_temp"]),
            brightness=int(snap["brightness"]) if snap.get("brightness") else None,
        )
        return
    if snap.get("brightness") is not None:
        set_light_brightness(host, int(snap["brightness"]))


def apply_rule(rule: dict) -> None:
    """Run rule steps; snapshot only hosts that have a restore step."""
    from homepchub.core.devices import get_power, set_light_hsv, set_power
    from homepchub.core.presets.base import apply_preset

    by_id = {d["id"]: d for d in (load_config().get("devices") or []) if d.get("id")}
    steps = list(rule.get("steps") or [])
    snaps: dict[str, dict] = {}
    for step in steps:
        if step.get("action") != ACTION_RESTORE:
            continue
        device = by_id.get(step.get("device_id"))
        host = (device or {}).get("host")
        if not host or host in snaps:
            continue
        try:
            snaps[host] = _snapshot_host(host)
        except Exception:
            snaps[host] = {"supported": False, "is_on": True}

    for step in steps:
        action = step.get("action")
        if action == ACTION_WAIT:
            ms = int(step.get("ms") or 0)
            if ms > 0:
                time.sleep(ms / 1000.0)
            continue
        device = by_id.get(step.get("device_id"))
        if not device:
            continue
        host = device.get("host")
        if not host:
            continue
        socket = step.get("socket")
        try:
            if action == ACTION_SET_HSV:
                set_power(host, True, socket=None)
                set_light_hsv(
                    host,
                    int(step["hue"]),
                    int(step["saturation"]),
                    int(step["brightness"]),
                )
            elif action == ACTION_RESTORE:
                snap = snaps.get(host)
                if snap:
                    _restore_host(host, snap)
            elif action == ACTION_APPLY_MODE:
                apply_preset(
                    host,
                    step["preset_id"],
                    device_id=device.get("id"),
                    run_actions=False,
                )
            elif action == ACTION_ON:
                set_power(host, True, socket=socket)
            elif action == ACTION_OFF:
                set_power(host, False, socket=socket)
            elif action == ACTION_TOGGLE:
                on = get_power(host, socket=socket)
                set_power(host, not on, socket=socket)
        except Exception:
            continue


def _enqueue(app_name: str | None) -> None:
    with _busy:
        _pending.append(app_name)
    _pending_wake.set()


async def _ensure_access(listener) -> bool:
    global _access_ok
    if _access_ok:
        return True
    status = listener.get_access_status()
    if status != unm.UserNotificationListenerAccessStatus.ALLOWED:
        status = await asyncio.wait_for(listener.request_access_async(), timeout=5)
    _access_ok = status == unm.UserNotificationListenerAccessStatus.ALLOWED
    return _access_ok


def _app_name_of(n) -> str | None:
    try:
        info = n.app_info
        if info is not None and info.display_info is not None:
            return str(info.display_info.display_name or "") or None
    except Exception:
        pass
    return None


async def _poll_once(listener) -> list[tuple[int, str | None]]:
    if not await _ensure_access(listener):
        return []
    notifications = await asyncio.wait_for(
        listener.get_notifications_async(un.NotificationKinds.TOAST),
        timeout=_POLL_TIMEOUT,
    )
    return [(int(n.id), n) for n in notifications]


def _listener_loop(run_id: int) -> None:
    global _seen_ids, _access_ok
    _seen_ids = None
    _access_ok = False
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    listener = unm.UserNotificationListener.current
    try:
        while not _stop.is_set() and run_id == _run_id:
            try:
                rows = loop.run_until_complete(_poll_once(listener))
                if run_id != _run_id:
                    break
                current = {nid for nid, _ in rows}
                if _seen_ids is None:
                    _seen_ids = set(current)
                else:
                    new_ids = current - _seen_ids
                    if new_ids:
                        by_obj = {nid: obj for nid, obj in rows}
                        for nid in new_ids:
                            _enqueue(_app_name_of(by_obj.get(nid)))
                    _seen_ids |= current
                    if len(_seen_ids) > _SEEN_CAP:
                        _seen_ids = set(current)
            except Exception:
                _access_ok = False
                _stop.wait(1.0)
                continue
            _stop.wait(_POLL_SECONDS)
    finally:
        loop.close()


def _worker_loop(run_id: int) -> None:
    while not _stop.is_set() and run_id == _run_id:
        _pending_wake.wait(0.5)
        _pending_wake.clear()
        while run_id == _run_id:
            with _busy:
                if not _pending:
                    break
                app_name = _pending.pop(0)
            settings = get_settings()
            if not settings["enabled"]:
                continue
            for rule in settings["rules"]:
                if not rule.get("enabled"):
                    continue
                if not _app_matches(rule.get("apps") or [], app_name):
                    continue
                try:
                    apply_rule(rule)
                except Exception:
                    pass
                break


def start_listener() -> None:
    global _thread, _worker, _run_id
    if not HAS_WINSDK:
        return
    if _thread is not None and _thread.is_alive():
        return
    _run_id += 1
    run_id = _run_id
    _stop.clear()
    _pending.clear()
    _pending_wake.clear()
    _worker = threading.Thread(
        target=_worker_loop, args=(run_id,), daemon=True, name="notify-worker"
    )
    _worker.start()
    _thread = threading.Thread(
        target=_listener_loop, args=(run_id,), daemon=True, name="notify-poll"
    )
    _thread.start()


def stop_listener() -> None:
    global _thread, _worker, _run_id
    _run_id += 1
    _stop.set()
    _pending_wake.set()
    # Do not join: poll may be blocked in WinRT for several seconds.
    _thread = None
    _worker = None


def start_if_enabled() -> None:
    if get_settings().get("enabled") and HAS_WINSDK:
        start_listener()
