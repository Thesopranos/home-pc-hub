import asyncio
import socket
import threading

from kasa import Credentials, Discover, Module
from kasa.feature import Feature

from homepchub.core.config import load_config

_loop = asyncio.new_event_loop()
threading.Thread(target=_loop.run_forever, daemon=True).start()

_device_cache: dict[str, object] = {}
_host_locks: dict[str, asyncio.Lock] = {}
_creds: Credentials | None = None


def set_credentials(email: str, password: str) -> None:
    global _creds
    _creds = Credentials(email, password)


def _ensure_creds() -> Credentials:
    global _creds
    if _creds is not None:
        return _creds
    creds = load_config()["credentials"]
    if not creds.get("tapo_email") or not creds.get("tapo_password"):
        raise RuntimeError("Tapo kimlik bilgileri yok")
    _creds = Credentials(creds["tapo_email"], creds["tapo_password"])
    return _creds


def _lock_for(host: str) -> asyncio.Lock:
    lock = _host_locks.get(host)
    if lock is None:
        lock = asyncio.Lock()
        _host_locks[host] = lock
    return lock


def _socket_info(dev) -> list[dict]:
    children = getattr(dev, "children", None) or []
    return [
        {"index": i, "alias": c.alias or None, "is_on": bool(c.is_on)}
        for i, c in enumerate(children)
    ]


def _light_features(dev) -> dict | None:
    modules = getattr(dev, "modules", None) or {}
    if Module.Light not in modules:
        return None
    light = modules[Module.Light]
    feats = {
        "brightness": bool(light.has_feature("brightness")),
        "hsv": bool(light.has_feature("hsv")),
        "color_temp": bool(light.has_feature("color_temp")),
    }
    return feats


def _classify(dev) -> str:
    if getattr(dev, "children", None):
        return "strip"
    if _light_features(dev) is not None:
        return "bulb"
    model = (getattr(dev, "model", None) or "").upper()
    if any(tag in model for tag in ("L5", "L9", "KL1", "KL5", "KB")):
        return "bulb"
    if hasattr(dev, "is_on"):
        return "plug"
    return "other"


def _device_snapshot(host: str, dev) -> dict:
    try:
        sockets = _socket_info(dev)
    except Exception:
        sockets = []
    try:
        kind = _classify(dev)
    except Exception:
        kind = "other"
    feats = None
    try:
        feats = _light_features(dev)
    except Exception:
        feats = None
    return {
        "host": host,
        "alias": getattr(dev, "alias", None),
        "model": getattr(dev, "model", None),
        "kind": kind,
        "has_light": feats is not None,
        "light_features": feats,
        "socket_count": len(sockets),
        "sockets": [{"index": s["index"], "alias": s["alias"]} for s in sockets],
    }


def _broadcast_targets() -> list[str]:
    """UDP discovery is flaky on multi-homed Windows; hit each /24 broadcast."""
    targets: set[str] = {"255.255.255.255"}
    ips: set[str] = set()

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except Exception:
        pass

    for ip in ips:
        if not _is_lan_ip(ip):
            continue
        parts = ip.split(".")
        targets.add(f"{parts[0]}.{parts[1]}.{parts[2]}.255")

    return sorted(targets)


def _is_lan_ip(ip: str) -> bool:
    """Skip loopback, link-local, and VPN/CGNAT ranges (e.g. Tailscale 100.x)."""
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        a, b = int(parts[0]), int(parts[1])
    except ValueError:
        return False
    if a == 127 or (a == 169 and b == 254):
        return False
    if a == 10:
        return True
    if a == 192 and b == 168:
        return True
    if a == 172 and 16 <= b <= 31:
        return True
    return False


async def _safe_disconnect(dev) -> None:
    try:
        await dev.disconnect()
    except Exception:
        pass


async def _discover_pass(
    creds: Credentials,
    *,
    discovery_timeout: int,
    discovery_packets: int,
) -> dict[str, object]:
    merged: dict[str, object] = {}
    for target in _broadcast_targets():
        try:
            found = await Discover.discover(
                credentials=creds,
                target=target,
                discovery_timeout=discovery_timeout,
                discovery_packets=discovery_packets,
            )
        except Exception:
            continue
        for host, dev in found.items():
            if host in merged:
                await _safe_disconnect(dev)
            else:
                merged[host] = dev
    return merged


async def _get_device(host: str, *, fresh: bool = False):
    creds = _ensure_creds()
    dev = _device_cache.get(host)
    if dev is None or fresh:
        if dev is not None:
            await _safe_disconnect(dev)
        dev = await Discover.discover_single(host, credentials=creds)
        await dev.update()
        _device_cache[host] = dev
    return dev


async def _with_device(host: str, action, *, needs_update: bool = False):
    async with _lock_for(host):
        try:
            dev = await _get_device(host)
            if needs_update:
                await dev.update()
            return await action(dev)
        except Exception:
            dev = await _get_device(host, fresh=True)
            if needs_update:
                await dev.update()
            return await action(dev)


def run(host: str, action, *, needs_update: bool = False):
    future = asyncio.run_coroutine_threadsafe(
        _with_device(host, action, needs_update=needs_update), _loop
    )
    return future.result(timeout=20)


def scan(timeout: int = 5) -> list[dict]:
    """Discover LAN devices. Retries across interfaces — UDP drops are common."""
    creds = _ensure_creds()

    async def _scan():
        # Pass 1 + 2: UDP broadcast often misses a bulb/plug on the first try.
        merged = await _discover_pass(
            creds, discovery_timeout=timeout, discovery_packets=5
        )
        second = await _discover_pass(
            creds, discovery_timeout=max(3, timeout - 1), discovery_packets=4
        )
        for host, dev in second.items():
            if host in merged:
                await _safe_disconnect(dev)
            else:
                merged[host] = dev

        # Direct probe for known hosts broadcast missed
        known_hosts = {
            d["host"] for d in load_config().get("devices", []) if d.get("host")
        }
        for host in known_hosts - set(merged):
            try:
                merged[host] = await Discover.discover_single(host, credentials=creds)
            except Exception:
                pass

        results = []
        for host, dev in list(merged.items()):
            try:
                try:
                    await asyncio.wait_for(dev.update(), timeout=10)
                except Exception:
                    # discovery payload often still has alias/model
                    pass
                results.append(_device_snapshot(host, dev))
            except Exception:
                results.append(
                    {
                        "host": host,
                        "alias": None,
                        "model": None,
                        "kind": "other",
                        "socket_count": 0,
                        "sockets": [],
                    }
                )
            finally:
                await _safe_disconnect(dev)
        return results

    interfaces = max(1, len(_broadcast_targets()))
    outer = timeout * 2 * interfaces + 25
    future = asyncio.run_coroutine_threadsafe(_scan(), _loop)
    return future.result(timeout=outer)


def get_status(host: str) -> dict:
    """Return {is_on, sockets: [{index, alias, is_on}, ...]}."""

    async def _get(dev):
        sockets = _socket_info(dev)
        if sockets:
            return {
                "is_on": any(s["is_on"] for s in sockets),
                "sockets": sockets,
            }
        return {"is_on": bool(dev.is_on), "sockets": []}

    return run(host, _get, needs_update=True)


def get_statuses(hosts: list[str]) -> dict[str, dict | None]:
    """Fetch many device statuses in parallel (per-host locks)."""

    async def _one(host: str):
        try:

            async def _get(dev):
                sockets = _socket_info(dev)
                if sockets:
                    return {
                        "is_on": any(s["is_on"] for s in sockets),
                        "sockets": sockets,
                    }
                return {"is_on": bool(dev.is_on), "sockets": []}

            return host, await _with_device(host, _get, needs_update=True)
        except Exception:
            return host, None

    async def _all():
        if not hosts:
            return {}
        pairs = await asyncio.gather(*[_one(h) for h in hosts])
        return {h: data for h, data in pairs}

    future = asyncio.run_coroutine_threadsafe(_all(), _loop)
    return future.result(timeout=max(20, 8 * max(1, len(hosts))))


def get_power(host: str, socket: int | None = None) -> bool:
    status = get_status(host)
    if socket is None:
        return bool(status["is_on"])
    for s in status["sockets"]:
        if s["index"] == socket:
            return bool(s["is_on"])
    raise IndexError(f"Soket yok: {socket}")


def set_power(host: str, on: bool, socket: int | None = None) -> None:
    async def _set(dev):
        if socket is None:
            target = dev
        else:
            children = getattr(dev, "children", None) or []
            if socket < 0 or socket >= len(children):
                raise IndexError(f"Soket yok: {socket}")
            target = children[socket]
        await (target.turn_on() if on else target.turn_off())

    run(host, _set)


def get_light_state(host: str) -> dict:
    """Live bulb capabilities + state. supported=False if no Light module."""

    async def _get(dev):
        feats = _light_features(dev)
        if feats is None:
            return {"supported": False}
        light = dev.modules[Module.Light]
        state = {
            "supported": True,
            "is_on": bool(dev.is_on),
            "features": feats,
            "brightness": None,
            "hsv": None,
            "color_temp": None,
            "color_temp_range": None,
        }
        if feats["brightness"]:
            state["brightness"] = int(light.brightness)
        if feats["hsv"]:
            h, s, v = light.hsv
            state["hsv"] = {"hue": int(h), "saturation": int(s), "value": int(v)}
        if feats["color_temp"]:
            state["color_temp"] = int(light.color_temp)
            ct = dev.modules.get(Module.ColorTemperature)
            if ct is not None:
                r = ct.valid_temperature_range
                state["color_temp_range"] = {"min": int(r.min), "max": int(r.max)}
            else:
                state["color_temp_range"] = {"min": 2500, "max": 6500}
        return state

    return run(host, _get, needs_update=True)


def set_light_brightness(host: str, value: int) -> None:
    value = max(1, min(100, int(value)))

    async def _set(dev):
        light = dev.modules[Module.Light]
        await light.set_brightness(value)

    run(host, _set)


def set_light_hsv(host: str, hue: int, saturation: int, value: int | None = None) -> None:
    hue = max(0, min(360, int(hue)))
    saturation = max(0, min(100, int(saturation)))
    if value is not None:
        value = max(1, min(100, int(value)))

    async def _set(dev):
        light = dev.modules[Module.Light]
        await light.set_hsv(hue, saturation, value)

    run(host, _set)


def set_light_color_temp(host: str, temp: int, brightness: int | None = None) -> None:
    temp = int(temp)

    async def _set(dev):
        light = dev.modules[Module.Light]
        ct = dev.modules.get(Module.ColorTemperature)
        if ct is not None:
            r = ct.valid_temperature_range
            temp_clamped = max(int(r.min), min(int(r.max), temp))
        else:
            temp_clamped = temp
        kwargs = {}
        if brightness is not None:
            kwargs["brightness"] = max(1, min(100, int(brightness)))
        await light.set_color_temp(temp_clamped, **kwargs)

    run(host, _set)


# Power / energy / LED etc. — strip energy is usually per-socket (child);
# LED and similar often live on the parent device.
_SKIP_FEATURE_IDS = {
    "state",  # already controlled by main toggles
    "hsv",
    "brightness",
    "color_temperature",  # bulbs use dedicated panel
}


def _serialize_feature_value(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if hasattr(value, "name"):  # Enum
        return value.name
    return str(value)


def _target_device(dev, socket: int | None):
    if socket is None:
        return dev
    children = getattr(dev, "children", None) or []
    if socket < 0 or socket >= len(children):
        raise IndexError(f"Soket yok: {socket}")
    return children[socket]


async def _ensure_target_updated(dev, socket: int | None):
    target = _target_device(dev, socket)
    if socket is not None:
        # Parent update often isn't enough for per-socket energy on Tapo strips
        try:
            await target.update()
        except Exception:
            pass
    return target


def _feature_list(target) -> list[dict]:
    features = getattr(target, "features", None) or {}
    out = []
    for fid, feat in features.items():
        if fid in _SKIP_FEATURE_IDS:
            continue
        ftype = feat.type
        item = {
            "id": fid,
            "name": feat.name or fid,
            "type": ftype.name if hasattr(ftype, "name") else str(ftype),
            "value": _serialize_feature_value(feat.value),
            "unit": feat.unit,
            "category": feat.category.name if getattr(feat, "category", None) else None,
            "writable": ftype
            in (
                Feature.Type.Switch,
                Feature.Type.Number,
                Feature.Type.Choice,
                Feature.Type.Action,
            ),
        }
        if ftype == Feature.Type.Number:
            try:
                item["minimum"] = feat.minimum_value
                item["maximum"] = feat.maximum_value
            except Exception:
                item["minimum"] = 0
                item["maximum"] = 100
        if ftype == Feature.Type.Choice:
            try:
                item["choices"] = list(feat.choices or [])
            except Exception:
                item["choices"] = []
        out.append(item)
    return out


def get_plug_features(host: str, socket: int | None = None) -> dict:
    """Return features for a plug or one strip socket (child).

    socket=None → whole device (parent). For strips, energy is usually on each child.
    """

    async def _get(dev):
        target = await _ensure_target_updated(dev, socket)
        feats = _feature_list(target)
        return {
            "scope": "socket" if socket is not None else "device",
            "socket": socket,
            "alias": getattr(target, "alias", None),
            "features": feats,
        }

    return run(host, _get, needs_update=True)


def set_plug_feature(
    host: str, feature_id: str, value, socket: int | None = None
) -> None:
    async def _set(dev):
        target = await _ensure_target_updated(dev, socket)
        features = getattr(target, "features", None) or {}
        if feature_id not in features:
            raise KeyError(f"Özellik yok: {feature_id}")
        feat = features[feature_id]
        if feat.type == Feature.Type.Action:
            await feat.set_value(True)
        elif feat.type == Feature.Type.Switch:
            await feat.set_value(bool(value))
        elif feat.type == Feature.Type.Number:
            await feat.set_value(float(value))
        else:
            await feat.set_value(value)

    run(host, _set)


def set_alias(host: str, alias: str, socket: int | None = None) -> str:
    """Rename device or one strip outlet on the hardware. Returns cleaned name."""
    alias = (alias or "").strip()
    if not alias:
        raise ValueError("empty alias")

    async def _set(dev):
        target = await _ensure_target_updated(dev, socket)
        await target.set_alias(alias)
        return alias

    return run(host, _set)


def drop_cache(host: str | None = None) -> None:
    async def _drop():
        hosts = [host] if host else list(_device_cache.keys())
        for h in hosts:
            dev = _device_cache.pop(h, None)
            if dev is not None:
                await _safe_disconnect(dev)

    future = asyncio.run_coroutine_threadsafe(_drop(), _loop)
    future.result(timeout=10)
