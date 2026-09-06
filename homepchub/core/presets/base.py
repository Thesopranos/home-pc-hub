"""Preset registry and apply helpers."""

from __future__ import annotations

import threading

from homepchub.core.config import load_config, save_config
from homepchub.core.devices import set_light_color_temp, set_power
from homepchub.core.presets import store as preset_store

REGISTRY: dict[str, dict] = {}
_active_dynamic: dict[str, list] = {}
_lock = threading.Lock()


def register(
    preset_id: str,
    *,
    label_key: str | None = None,
    label: str | None = None,
    apply,
    stop=None,
    editable: bool = False,
    custom: bool = False,
) -> None:
    REGISTRY[preset_id] = {
        "label_key": label_key,
        "label": label,
        "apply": apply,
        "stop": stop,
        "editable": bool(editable),
        "custom": bool(custom),
    }


def unregister(preset_id: str) -> None:
    REGISTRY.pop(preset_id, None)


def list_preset_ids() -> list[str]:
    return list(REGISTRY.keys())


def list_editable_ids() -> list[str]:
    return [pid for pid, e in REGISTRY.items() if e.get("editable")]


def preset_label(preset_id: str) -> str:
    entry = REGISTRY.get(preset_id) or {}
    if entry.get("label"):
        return str(entry["label"])
    key = entry.get("label_key")
    if key:
        from homepchub.i18n import t

        return t(key)
    return preset_id


def stop_dynamic(host: str) -> None:
    with _lock:
        stops = _active_dynamic.pop(host, [])
    for fn in stops:
        try:
            fn()
        except Exception:
            pass


def _remember_dynamic(host: str, stop_fn) -> None:
    with _lock:
        _active_dynamic.setdefault(host, []).append(stop_fn)


def apply_static(host: str, kelvin: int, brightness: int) -> None:
    set_power(host, True, socket=None)
    set_light_color_temp(host, int(kelvin), brightness=int(brightness))


def apply_static_preset(host: str, preset_id: str) -> None:
    kelvin, brightness = preset_store.get_static_params(preset_id)
    apply_static(host, kelvin, brightness)


def set_device_preset(device_id: str, preset_id: str | None) -> None:
    cfg = load_config()
    for d in cfg.get("devices") or []:
        if d["id"] == device_id:
            d["active_preset"] = preset_id
            save_config(cfg)
            return


def apply_preset(
    host: str,
    preset_id: str,
    *,
    device_id: str | None = None,
    run_actions: bool = True,
) -> None:
    entry = REGISTRY.get(preset_id)
    if not entry:
        raise KeyError(preset_id)
    stop_dynamic(host)
    entry["apply"](host)
    stop_fn = entry.get("stop")
    if stop_fn:

        def _bound(fn=stop_fn, h=host):
            fn(h)

        _remember_dynamic(host, _bound)
    if device_id:
        set_device_preset(device_id, preset_id)
    if run_actions:
        _run_linked_actions(preset_id, skip_host=host)


def _run_linked_actions(preset_id: str, *, skip_host: str) -> None:
    """Run extra device actions configured for this mode (no nested cascades)."""
    from homepchub.core.devices import get_power, set_power

    cfg = load_config()
    by_id = {d["id"]: d for d in (cfg.get("devices") or []) if d.get("id")}
    for step in preset_store.get_actions(preset_id):
        device = by_id.get(step["device_id"])
        if not device:
            continue
        host = device.get("host")
        if not host or host == skip_host:
            continue
        socket = step.get("socket")
        action = step.get("action")
        try:
            if action == preset_store.ACTION_APPLY_MODE:
                apply_preset(
                    host,
                    preset_id,
                    device_id=device.get("id"),
                    run_actions=False,
                )
            elif action == preset_store.ACTION_ON:
                set_power(host, True, socket=socket)
            elif action == preset_store.ACTION_OFF:
                set_power(host, False, socket=socket)
            elif action == preset_store.ACTION_TOGGLE:
                on = get_power(host, socket=socket)
                set_power(host, not on, socket=socket)
        except Exception:
            continue


def _make_custom_apply(preset_id: str):
    def _apply(host: str, pid=preset_id) -> None:
        apply_static_preset(host, pid)

    return _apply


def reload_custom_presets() -> None:
    """Drop previous customs from registry and load from config."""
    for pid in list(REGISTRY):
        if REGISTRY[pid].get("custom"):
            unregister(pid)
    for item in preset_store.list_custom():
        pid = item["id"]
        register(
            pid,
            label=item.get("label") or pid,
            apply=_make_custom_apply(pid),
            editable=True,
            custom=True,
        )
