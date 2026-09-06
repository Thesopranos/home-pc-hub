"""Global hotkeys via keyboard hook (Home Hub style) + capture for settings UI.

keyboard.add_hotkey() can stick when Ctrl is held across sequential keys —
we match the held-key set ourselves instead.
"""

from __future__ import annotations

import functools
import threading
from typing import Callable

from homepchub.core.config import load_config, save_config

try:
    import keyboard
except ImportError:  # pragma: no cover
    keyboard = None  # type: ignore

_MODIFIER_ALIASES = {
    "left ctrl": "ctrl",
    "right ctrl": "ctrl",
    "left alt": "alt",
    "right alt": "alt",
    "left shift": "shift",
    "right shift": "shift",
    "left windows": "windows",
    "right windows": "windows",
}
_MODIFIERS = frozenset({"ctrl", "alt", "shift", "windows"})
_MOD_ORDER = ("ctrl", "alt", "shift", "windows")

_pressed: set[str] = set()
_hotkey_map: dict[frozenset[str], Callable[[], None]] = {}
_hook_installed = False
_capturing = False
_capture_cb: Callable[[str | None], None] | None = None
_actions: dict[str, Callable[[], None]] = {}


def _normalize_key(name: str) -> str:
    return _MODIFIER_ALIASES.get(name, name)


def combo_keys(combo: str) -> frozenset[str]:
    return frozenset(
        _normalize_key(part.strip()) for part in (combo or "").split("+") if part.strip()
    )


def format_combo(keys: set[str] | frozenset[str]) -> str:
    mods = [m for m in _MOD_ORDER if m in keys]
    rest = sorted(k for k in keys if k not in _MODIFIERS)
    return "+".join(mods + rest)


def target_key(device_id: str, socket: int | None = None) -> str:
    if socket is None:
        return str(device_id)
    return f"{device_id}:{int(socket)}"


def parse_target_key(key: str) -> tuple[str, int | None]:
    if ":" in key:
        did, sock = key.rsplit(":", 1)
        try:
            return did, int(sock)
        except ValueError:
            return key, None
    return key, None


def get_hotkeys() -> dict:
    cfg = load_config()
    bucket = cfg.get("hotkeys")
    if not isinstance(bucket, dict):
        bucket = {}
    return {
        "flyout": str(bucket.get("flyout") or ""),
        "settings": str(bucket.get("settings") or ""),
        "targets": dict(bucket.get("targets") or {}),
    }


def set_hotkeys(*, flyout: str, settings: str, targets: dict[str, str]) -> None:
    cfg = load_config()
    cleaned = {k: str(v).strip() for k, v in targets.items() if str(v).strip()}
    cfg["hotkeys"] = {
        "flyout": (flyout or "").strip(),
        "settings": (settings or "").strip(),
        "targets": cleaned,
    }
    save_config(cfg)
    reload()


def set_actions(
    *,
    on_flyout: Callable[[], None] | None = None,
    on_settings: Callable[[], None] | None = None,
) -> None:
    if on_flyout is not None:
        _actions["flyout"] = on_flyout
    if on_settings is not None:
        _actions["settings"] = on_settings


def _toggle_target(device_id: str, socket: int | None) -> None:
    from homepchub.core.devices import get_power, set_power

    devices = load_config().get("devices") or []
    device = next((d for d in devices if d.get("id") == device_id), None)
    if not device:
        return
    host = device["host"]
    try:
        on = get_power(host, socket)
        set_power(host, not on, socket=socket)
    except Exception:
        pass


def _on_key_event(event) -> None:
    name = _normalize_key(event.name)
    if event.event_type == keyboard.KEY_DOWN:
        if name in _pressed:
            return
        _pressed.add(name)
        if _capturing:
            if name == "esc":
                end_capture(None)  # cancel — keep previous
                return
            if name not in _MODIFIERS:
                end_capture(format_combo(_pressed))
            return
        callback = _hotkey_map.get(frozenset(_pressed))
        if callback:
            threading.Thread(target=callback, daemon=True).start()
    elif event.event_type == keyboard.KEY_UP:
        _pressed.discard(name)


def begin_capture(on_done: Callable[[str | None], None]) -> bool:
    """Start listening for the next key combo. Returns False if keyboard missing."""
    global _capturing, _capture_cb
    if keyboard is None:
        return False
    _ensure_hook()
    _pressed.clear()
    _capturing = True
    _capture_cb = on_done
    return True


def end_capture(combo: str | None) -> None:
    global _capturing, _capture_cb
    cb = _capture_cb
    _capturing = False
    _capture_cb = None
    _pressed.clear()
    if cb is not None:
        cb(combo)


def cancel_capture() -> None:
    if _capturing:
        end_capture(None)


def _ensure_hook() -> None:
    global _hook_installed
    if keyboard is None or _hook_installed:
        return
    keyboard.hook(_on_key_event)
    _hook_installed = True


def reload() -> None:
    """Rebuild combo → callback map from config + registered UI actions."""
    _hotkey_map.clear()
    if keyboard is None:
        return
    hk = get_hotkeys()
    if hk["flyout"] and "flyout" in _actions:
        _hotkey_map[combo_keys(hk["flyout"])] = _actions["flyout"]
    if hk["settings"] and "settings" in _actions:
        _hotkey_map[combo_keys(hk["settings"])] = _actions["settings"]
    for key, combo in (hk["targets"] or {}).items():
        if not combo:
            continue
        did, sock = parse_target_key(key)
        _hotkey_map[combo_keys(combo)] = functools.partial(_toggle_target, did, sock)
    _ensure_hook()


def available() -> bool:
    return keyboard is not None
