import json
import uuid
from pathlib import Path

APP_DATA_DIR = Path.home() / "AppData" / "Roaming" / "HomePcHub"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = APP_DATA_DIR / "config.json"

DEFAULTS = {
    "credentials": {"tapo_email": "", "tapo_password": ""},
    "devices": [],
    "theme": "dark",
    "language": "tr",
    "screen_sync_monitor": 0,
    "screen_sync_boost": 10,
    "presets": {"overrides": {}, "custom": [], "actions": {}},
    "hotkeys": {
        "flyout": "ctrl+shift+h",
        "settings": "",
        "targets": {},
        "shared": [],
    },
}


def _merge(defaults: dict, overrides: dict) -> dict:
    result = dict(defaults)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return json.loads(json.dumps(DEFAULTS))
    saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return _merge(DEFAULTS, saved)


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def set_theme(mode: str) -> None:
    if mode not in ("dark", "light"):
        raise ValueError(mode)
    cfg = load_config()
    cfg["theme"] = mode
    save_config(cfg)


def get_theme_mode() -> str:
    mode = load_config().get("theme", "dark")
    return mode if mode in ("dark", "light") else "dark"


def get_screen_sync_monitor() -> int:
    try:
        return max(0, int(load_config().get("screen_sync_monitor", 0)))
    except (TypeError, ValueError):
        return 0


def get_screen_sync_boost() -> int:
    try:
        return max(0, min(100, int(load_config().get("screen_sync_boost", 10))))
    except (TypeError, ValueError):
        return 10


def set_screen_sync_settings(*, monitor: int | None = None, boost: int | None = None) -> None:
    cfg = load_config()
    if monitor is not None:
        cfg["screen_sync_monitor"] = max(0, int(monitor))
    if boost is not None:
        cfg["screen_sync_boost"] = max(0, min(100, int(boost)))
    save_config(cfg)


def _prompt_credentials(current: dict) -> dict | None:
    import tkinter as tk
    from tkinter import ttk

    from homepchub.assets import logo_photo
    from homepchub.i18n import t
    from homepchub.ui.theme import FONTS, apply_ttk, get_theme
    from homepchub.ui.winchrome import dress_window

    mode = get_theme_mode()
    theme = get_theme(mode)
    root = tk.Tk()
    root.title(t("setup.title"))
    root.resizable(False, False)
    root.configure(bg=theme["bg"])
    dress_window(root, theme, dark=mode == "dark")
    style = ttk.Style(root)
    apply_ttk(style, theme)

    wrap = ttk.Frame(root, padding=24)
    wrap.grid()

    try:
        root._setup_logo = logo_photo(root, mode, height=40)
        ttk.Label(wrap, image=root._setup_logo).grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
    except Exception:
        ttk.Label(wrap, text="Home Pc Hub", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
    ttk.Label(
        wrap,
        text=t("setup.blurb"),
        style="Muted.TLabel",
    ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 16))

    ttk.Label(wrap, text=t("setup.email")).grid(row=2, column=0, sticky="w")
    email_entry = ttk.Entry(wrap, width=36, font=FONTS["ui"])
    email_entry.insert(0, current.get("tapo_email", ""))
    email_entry.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 12))

    ttk.Label(wrap, text=t("setup.password")).grid(row=4, column=0, sticky="w")
    password_entry = ttk.Entry(wrap, width=36, show="•", font=FONTS["ui"])
    password_entry.insert(0, current.get("tapo_password", ""))
    password_entry.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(4, 16))

    result: dict | None = {}

    def submit():
        nonlocal result
        email = email_entry.get().strip()
        password = password_entry.get()
        if not email or not password:
            result = None
            root.destroy()
            return
        result = {"tapo_email": email, "tapo_password": password}
        root.destroy()

    def cancel():
        nonlocal result
        result = None
        root.destroy()

    btns = ttk.Frame(wrap)
    btns.grid(row=6, column=0, columnspan=2, sticky="e")
    ttk.Button(btns, text=t("setup.cancel"), style="Ghost.TButton", command=cancel).pack(
        side="left", padx=(0, 8)
    )
    ttk.Button(btns, text=t("setup.save"), style="Accent.TButton", command=submit).pack(
        side="left"
    )

    root.protocol("WM_DELETE_WINDOW", cancel)
    email_entry.focus()
    root.mainloop()
    return result

def ensure_credentials() -> dict | None:
    cfg = load_config()
    creds = cfg["credentials"]
    if creds.get("tapo_email") and creds.get("tapo_password"):
        return creds

    prompted = _prompt_credentials(creds)
    if not prompted:
        return None
    cfg["credentials"] = prompted
    save_config(cfg)
    return prompted


def add_device(
    host: str,
    alias: str | None,
    model: str | None,
    kind: str,
    *,
    socket_count: int = 0,
    sockets: list[dict] | None = None,
    has_light: bool = False,
    light_features: dict | None = None,
) -> dict:
    cfg = load_config()
    existing = {d["host"] for d in cfg["devices"]}
    if host in existing:
        raise ValueError(f"Cihaz zaten kayıtlı: {host}")
    device = {
        "id": str(uuid.uuid4()),
        "host": host,
        "alias": alias,
        "model": model,
        "kind": kind,
        "has_light": bool(has_light or kind == "bulb"),
        "light_features": light_features,
        "socket_count": int(socket_count or 0),
        "sockets": sockets or [],
    }
    cfg["devices"].append(device)
    save_config(cfg)
    return device


def remove_device(device_id: str) -> None:
    cfg = load_config()
    cfg["devices"] = [d for d in cfg["devices"] if d["id"] != device_id]
    save_config(cfg)


def update_alias(
    device_id: str, alias: str, *, socket: int | None = None
) -> None:
    """Update saved device name, or one outlet name when socket is set."""
    cfg = load_config()
    for d in cfg["devices"]:
        if d["id"] != device_id:
            continue
        if socket is None:
            d["alias"] = alias
        else:
            sockets = list(d.get("sockets") or [])
            found = False
            for s in sockets:
                if int(s["index"]) == int(socket):
                    s["alias"] = alias
                    found = True
                    break
            if not found:
                sockets.append({"index": int(socket), "alias": alias})
            d["sockets"] = sockets
        save_config(cfg)
        return
    raise KeyError(f"device not found: {device_id}")


def _schedule_bucket(device: dict, socket: int | None) -> list:
    if socket is None:
        return list(device.get("schedules") or [])
    for s in device.get("sockets") or []:
        if int(s.get("index")) == int(socket):
            return list(s.get("schedules") or [])
    return []


def get_schedules(device_id: str, socket: int | None = None) -> list[dict]:
    cfg = load_config()
    for d in cfg["devices"]:
        if d["id"] == device_id:
            return _schedule_bucket(d, socket)
    return []


def set_schedules(
    device_id: str, schedules: list[dict], *, socket: int | None = None
) -> None:
    cfg = load_config()
    for d in cfg["devices"]:
        if d["id"] != device_id:
            continue
        cleaned = list(schedules or [])
        if socket is None:
            d["schedules"] = cleaned
        else:
            sockets = list(d.get("sockets") or [])
            found = False
            for s in sockets:
                if int(s.get("index")) == int(socket):
                    s["schedules"] = cleaned
                    found = True
                    break
            if not found:
                sockets.append({"index": int(socket), "schedules": cleaned})
            d["sockets"] = sockets
        save_config(cfg)
        return
    raise KeyError(f"device not found: {device_id}")


def upsert_schedule(
    device_id: str, rule: dict, *, socket: int | None = None
) -> dict:
    rules = get_schedules(device_id, socket)
    rid = rule.get("id") or str(uuid.uuid4())
    rule = {**rule, "id": rid}
    out = []
    replaced = False
    for r in rules:
        if r.get("id") == rid:
            out.append(rule)
            replaced = True
        else:
            out.append(r)
    if not replaced:
        out.append(rule)
    set_schedules(device_id, out, socket=socket)
    return rule


def delete_schedule(
    device_id: str, schedule_id: str, *, socket: int | None = None
) -> None:
    rules = [r for r in get_schedules(device_id, socket) if r.get("id") != schedule_id]
    set_schedules(device_id, rules, socket=socket)


def iter_schedule_targets() -> list[dict]:
    """Yield {device_id, host, socket, schedules} for every programmable target."""
    out = []
    for d in load_config().get("devices") or []:
        if d.get("schedules"):
            out.append(
                {
                    "device_id": d["id"],
                    "host": d["host"],
                    "socket": None,
                    "schedules": list(d["schedules"]),
                }
            )
        for s in d.get("sockets") or []:
            if s.get("schedules"):
                out.append(
                    {
                        "device_id": d["id"],
                        "host": d["host"],
                        "socket": int(s["index"]),
                        "schedules": list(s["schedules"]),
                    }
                )
    return out


def merge_sockets(existing: list | None, discovered: list) -> list[dict]:
    """Keep local fields (e.g. schedules) when refreshing outlet metadata from LAN."""
    by_index = {int(s.get("index")): s for s in (existing or [])}
    out = []
    for s in discovered:
        idx = int(s["index"])
        prev = by_index.get(idx, {})
        entry = {
            "index": idx,
            "alias": s.get("alias") if s.get("alias") is not None else prev.get("alias"),
        }
        if prev.get("schedules"):
            entry["schedules"] = list(prev["schedules"])
        out.append(entry)
    return out


def socket_identity(sockets: list | None) -> list[dict]:
    """Compare-only view: index + alias (ignores schedules)."""
    return [
        {"index": int(s.get("index")), "alias": s.get("alias")}
        for s in (sockets or [])
    ]


def demo():
    merged = _merge(DEFAULTS, {"credentials": {"tapo_email": "a@b.c"}})
    assert merged["credentials"]["tapo_email"] == "a@b.c"
    assert merged["credentials"]["tapo_password"] == ""
    assert merged["devices"] == []
    kept = merge_sockets(
        [{"index": 0, "alias": "A", "schedules": [{"id": "1"}]}],
        [{"index": 0, "alias": "A"}, {"index": 1, "alias": "B"}],
    )
    assert kept[0]["schedules"] == [{"id": "1"}]
    assert "schedules" not in kept[1]
    print("ok")


if __name__ == "__main__":
    demo()
