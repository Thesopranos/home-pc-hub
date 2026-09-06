"""Persisted ambient preset overrides, customs, and linked device actions."""

from __future__ import annotations

import uuid

from homepchub.core.config import load_config, save_config

# Built-in static recipes (Kelvin + brightness). Dynamic modes are not here.
STATIC_DEFAULTS: dict[str, dict] = {
    "reading": {"kelvin": 2890, "brightness": 90},
    "work": {"kelvin": 4291, "brightness": 85},
    "movie": {"kelvin": 2700, "brightness": 15},
    "relax": {"kelvin": 2500, "brightness": 40},
}

# Linked action kinds
ACTION_APPLY_MODE = "apply_mode"
ACTION_ON = "on"
ACTION_OFF = "off"
ACTION_TOGGLE = "toggle"


def _presets_bucket(cfg: dict | None = None) -> dict:
    cfg = cfg if cfg is not None else load_config()
    bucket = cfg.get("presets")
    if not isinstance(bucket, dict):
        bucket = {}
        cfg["presets"] = bucket
    bucket.setdefault("overrides", {})
    bucket.setdefault("custom", [])
    bucket.setdefault("actions", {})
    return bucket


def get_static_params(preset_id: str) -> tuple[int, int]:
    """Return (kelvin, brightness) for a static built-in or custom id."""
    cfg = load_config()
    bucket = _presets_bucket(cfg)
    for item in bucket.get("custom") or []:
        if item.get("id") == preset_id:
            return (
                max(2500, min(6500, int(item.get("kelvin", 3000)))),
                max(1, min(100, int(item.get("brightness", 50)))),
            )
    base = dict(STATIC_DEFAULTS.get(preset_id) or {"kelvin": 3000, "brightness": 50})
    ov = (bucket.get("overrides") or {}).get(preset_id) or {}
    kelvin = int(ov.get("kelvin", base["kelvin"]))
    brightness = int(ov.get("brightness", base["brightness"]))
    return max(2500, min(6500, kelvin)), max(1, min(100, brightness))


def set_static_override(preset_id: str, *, kelvin: int, brightness: int) -> None:
    if preset_id not in STATIC_DEFAULTS:
        raise KeyError(preset_id)
    cfg = load_config()
    bucket = _presets_bucket(cfg)
    bucket["overrides"][preset_id] = {
        "kelvin": max(2500, min(6500, int(kelvin))),
        "brightness": max(1, min(100, int(brightness))),
    }
    save_config(cfg)


def reset_static_override(preset_id: str) -> None:
    cfg = load_config()
    bucket = _presets_bucket(cfg)
    bucket.get("overrides", {}).pop(preset_id, None)
    save_config(cfg)


def list_custom() -> list[dict]:
    return list(_presets_bucket().get("custom") or [])


def add_custom(*, label: str, kelvin: int, brightness: int) -> dict:
    label = (label or "").strip()
    if not label:
        raise ValueError("empty label")
    item = {
        "id": f"custom_{uuid.uuid4().hex[:10]}",
        "label": label,
        "kelvin": max(2500, min(6500, int(kelvin))),
        "brightness": max(1, min(100, int(brightness))),
    }
    cfg = load_config()
    bucket = _presets_bucket(cfg)
    customs = list(bucket.get("custom") or [])
    customs.append(item)
    bucket["custom"] = customs
    save_config(cfg)
    return item


def update_custom(
    preset_id: str,
    *,
    label: str | None = None,
    kelvin: int | None = None,
    brightness: int | None = None,
) -> dict:
    cfg = load_config()
    bucket = _presets_bucket(cfg)
    customs = list(bucket.get("custom") or [])
    for i, item in enumerate(customs):
        if item.get("id") != preset_id:
            continue
        updated = dict(item)
        if label is not None:
            cleaned = label.strip()
            if not cleaned:
                raise ValueError("empty label")
            updated["label"] = cleaned
        if kelvin is not None:
            updated["kelvin"] = max(2500, min(6500, int(kelvin)))
        if brightness is not None:
            updated["brightness"] = max(1, min(100, int(brightness)))
        customs[i] = updated
        bucket["custom"] = customs
        save_config(cfg)
        return updated
    raise KeyError(preset_id)


def delete_custom(preset_id: str) -> None:
    cfg = load_config()
    bucket = _presets_bucket(cfg)
    bucket["custom"] = [
        c for c in (bucket.get("custom") or []) if c.get("id") != preset_id
    ]
    (bucket.get("actions") or {}).pop(preset_id, None)
    save_config(cfg)


def _clean_action(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    device_id = raw.get("device_id")
    action = raw.get("action")
    if not device_id or action not in (
        ACTION_APPLY_MODE,
        ACTION_ON,
        ACTION_OFF,
        ACTION_TOGGLE,
    ):
        return None
    socket = raw.get("socket")
    if socket is not None:
        try:
            socket = int(socket)
        except (TypeError, ValueError):
            socket = None
    return {
        "device_id": str(device_id),
        "socket": socket,
        "action": action,
    }


def get_actions(preset_id: str) -> list[dict]:
    raw = (_presets_bucket().get("actions") or {}).get(preset_id) or []
    out = []
    for item in raw:
        cleaned = _clean_action(item)
        if cleaned:
            out.append(cleaned)
    return out


def set_actions(preset_id: str, actions: list[dict]) -> None:
    cfg = load_config()
    bucket = _presets_bucket(cfg)
    cleaned = []
    for item in actions or []:
        c = _clean_action(item)
        if c:
            cleaned.append(c)
    bucket.setdefault("actions", {})[preset_id] = cleaned
    save_config(cfg)


def iter_action_targets() -> list[dict]:
    """Selectable targets for linked actions: bulbs and plugs/outlets."""
    from homepchub.i18n import t

    out: list[dict] = []
    for d in load_config().get("devices") or []:
        did = d.get("id")
        host = d.get("host")
        if not did or not host:
            continue
        name = d.get("alias") or host
        kind = d.get("kind") or "other"
        socket_count = int(d.get("socket_count") or 0)
        is_bulb = kind == "bulb" or bool(d.get("has_light"))
        is_multi = kind == "strip" or socket_count > 0

        if is_multi:
            sockets = d.get("sockets") or [
                {"index": i} for i in range(socket_count)
            ]
            for s in sockets:
                idx = int(s["index"])
                sock_name = s.get("alias") or t("status.socket_n", n=idx + 1)
                out.append(
                    {
                        "device_id": did,
                        "host": host,
                        "socket": idx,
                        "kind": "plug",
                        "label": f"{name} — {sock_name}",
                        "key": f"{did}:{idx}",
                    }
                )
        elif is_bulb:
            out.append(
                {
                    "device_id": did,
                    "host": host,
                    "socket": None,
                    "kind": "bulb",
                    "label": name,
                    "key": f"{did}:",
                }
            )
        else:
            out.append(
                {
                    "device_id": did,
                    "host": host,
                    "socket": None,
                    "kind": "plug",
                    "label": name,
                    "key": f"{did}:",
                }
            )
    return out
