"""Named scenes: ordered device steps (ambient / on / off / toggle / wait)."""

from __future__ import annotations

import time
import uuid

from homepchub.core.config import load_config, save_config
from homepchub.core.presets import store as preset_store

ACTION_APPLY_MODE = preset_store.ACTION_APPLY_MODE
ACTION_ON = preset_store.ACTION_ON
ACTION_OFF = preset_store.ACTION_OFF
ACTION_TOGGLE = preset_store.ACTION_TOGGLE
ACTION_WAIT = "wait"

_MAX_WAIT_MS = 600_000  # 10 minutes


def _clean_step(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    action = raw.get("action")
    if action == ACTION_WAIT:
        try:
            ms = int(raw.get("ms", 0))
        except (TypeError, ValueError):
            return None
        ms = max(0, min(_MAX_WAIT_MS, ms))
        return {"action": ACTION_WAIT, "ms": ms}

    device_id = raw.get("device_id")
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


def list_scenes() -> list[dict]:
    raw = load_config().get("scenes") or []
    out = []
    for item in raw:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        label = (item.get("label") or "").strip() or item["id"]
        steps = []
        for s in item.get("steps") or []:
            cleaned = _clean_step(s)
            if cleaned:
                steps.append(cleaned)
        out.append({"id": str(item["id"]), "label": label, "steps": steps})
    return out


def get_scene(scene_id: str) -> dict | None:
    for scene in list_scenes():
        if scene["id"] == scene_id:
            return scene
    return None


def upsert_scene(
    *,
    scene_id: str | None,
    label: str,
    steps: list[dict],
) -> dict:
    label = (label or "").strip()
    if not label:
        raise ValueError("empty label")
    cleaned = []
    for s in steps or []:
        c = _clean_step(s)
        if c:
            cleaned.append(c)
    cfg = load_config()
    scenes = list(cfg.get("scenes") or [])
    if scene_id:
        for i, item in enumerate(scenes):
            if isinstance(item, dict) and item.get("id") == scene_id:
                updated = {"id": scene_id, "label": label, "steps": cleaned}
                scenes[i] = updated
                cfg["scenes"] = scenes
                save_config(cfg)
                return updated
        raise KeyError(scene_id)
    created = {
        "id": f"scene_{uuid.uuid4().hex[:10]}",
        "label": label,
        "steps": cleaned,
    }
    scenes.append(created)
    cfg["scenes"] = scenes
    save_config(cfg)
    return created


def delete_scene(scene_id: str) -> None:
    cfg = load_config()
    cfg["scenes"] = [
        s
        for s in (cfg.get("scenes") or [])
        if not (isinstance(s, dict) and s.get("id") == scene_id)
    ]
    save_config(cfg)


def apply_scene(scene_id: str) -> None:
    """Run scene steps in order. Linked ambient actions are not cascaded."""
    from homepchub.core.devices import get_power, set_power
    from homepchub.core.presets.base import apply_preset

    scene = get_scene(scene_id)
    if not scene:
        raise KeyError(scene_id)
    by_id = {d["id"]: d for d in (load_config().get("devices") or []) if d.get("id")}
    for step in scene["steps"]:
        action = step.get("action")
        if action == ACTION_WAIT:
            try:
                ms = max(0, min(_MAX_WAIT_MS, int(step.get("ms", 0))))
            except (TypeError, ValueError):
                ms = 0
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
            if action == ACTION_APPLY_MODE:
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
