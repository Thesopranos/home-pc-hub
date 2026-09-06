"""Local socket/device schedules - daily…yearly + on/off loops.

# ponytail: ~20s poll (not second-precise). Use OS task scheduler if you need exact second timing.
"""

from __future__ import annotations

import calendar
import threading
from datetime import datetime, timedelta

from homepchub.core.config import iter_schedule_targets, set_schedules
from homepchub.core.devices import get_power, set_power

_POLL_S = 20
_stop = threading.Event()
_thread: threading.Thread | None = None
_lock = threading.Lock()
# last fire key -> "YYYY-MM-DD HH:MM" to avoid double-fire in the same minute
_fired: dict[str, str] = {}


def _parse_hm(value: str) -> tuple[int, int]:
    parts = (value or "00:00").strip().split(":")
    return int(parts[0]), int(parts[1] if len(parts) > 1 else 0)


def _minute_key(now: datetime) -> str:
    return now.strftime("%Y-%m-%d %H:%M")


def _match_period(rule: dict, now: datetime) -> bool:
    kind = rule.get("kind") or "daily"
    hh, mm = _parse_hm(rule.get("time") or "00:00")
    if now.hour != hh or now.minute != mm:
        return False

    if kind == "once":
        date_s = (rule.get("date") or "").strip()
        return date_s == now.strftime("%Y-%m-%d")

    if kind == "daily":
        return True

    if kind == "weekly":
        days = rule.get("weekdays")
        if not days:
            return False
        # Monday=0 … Sunday=6
        return int(now.weekday()) in {int(d) for d in days}

    if kind == "monthly":
        day = int(rule.get("day_of_month") or 0)
        if day < 1:
            return False
        last = calendar.monthrange(now.year, now.month)[1]
        return now.day == min(day, last)

    if kind == "yearly":
        month = int(rule.get("month") or 0)
        day = int(rule.get("day") or 0)
        if month < 1 or day < 1:
            return False
        last = calendar.monthrange(now.year, month)[1]
        return now.month == month and now.day == min(day, last)

    return False


def desired_loop_on(rule: dict, now: datetime) -> bool | None:
    """Return desired on/off for a loop rule, or None if inactive."""
    if not rule.get("enabled", True):
        return None
    on_m = max(0, int(rule.get("on_minutes") or 0))
    off_m = max(0, int(rule.get("off_minutes") or 0))
    if on_m == 0 and off_m == 0:
        return None
    period = (on_m + off_m) * 60
    if period <= 0:
        return None
    start_s = rule.get("loop_start")
    if not start_s:
        start_s = now.isoformat(timespec="seconds")
        rule["loop_start"] = start_s
        # caller may persist
    try:
        start = datetime.fromisoformat(start_s)
    except ValueError:
        start = now
        rule["loop_start"] = now.isoformat(timespec="seconds")
    elapsed = (now - start).total_seconds()
    if elapsed < 0:
        elapsed = 0
    pos = elapsed % period
    return pos < (on_m * 60)


def evaluate_rule(rule: dict, now: datetime) -> bool | str | None:
    """Return desired power state, 'toggle', or None if this rule does nothing now."""
    if not rule.get("enabled", True):
        return None
    kind = rule.get("kind") or "daily"
    if kind == "loop":
        return desired_loop_on(rule, now)

    if not _match_period(rule, now):
        return None
    action = (rule.get("action") or "on").lower()
    if action == "off":
        return False
    if action == "toggle":
        return "toggle"
    return True


def _resolve_want(host: str, socket, state) -> bool | None:
    if state is None:
        return None
    if state == "toggle":
        try:
            return not get_power(host, socket)
        except Exception:
            return None
    return bool(state)


def _fire_key(device_id: str, socket, rule_id: str) -> str:
    return f"{device_id}:{socket}:{rule_id}"


def tick(now: datetime | None = None) -> list[tuple]:
    """Apply due schedules. Returns list of (host, socket, on) applied."""
    now = now or datetime.now()
    minute = _minute_key(now)
    applied = []
    with _lock:
        for target in iter_schedule_targets():
            host = target["host"]
            socket = target["socket"]
            device_id = target["device_id"]
            dirty_rules = False
            want: bool | None = None
            for rule in target["schedules"]:
                kind = rule.get("kind") or "daily"
                if kind == "loop":
                    before = rule.get("loop_start")
                    state = evaluate_rule(rule, now)
                    if rule.get("loop_start") != before:
                        dirty_rules = True
                    resolved = _resolve_want(host, socket, state)
                    if resolved is None:
                        continue
                    want = resolved
                    continue

                state = evaluate_rule(rule, now)
                if state is None:
                    continue
                key = _fire_key(device_id, socket, rule.get("id") or "")
                if _fired.get(key) == minute:
                    continue
                resolved = _resolve_want(host, socket, state)
                if resolved is None:
                    continue
                _fired[key] = minute
                want = resolved
                if kind == "once":
                    rule["enabled"] = False
                    dirty_rules = True

            if dirty_rules:
                try:
                    set_schedules(device_id, target["schedules"], socket=socket)
                except Exception:
                    pass

            if want is None:
                continue
            try:
                set_power(host, want, socket=socket)
                applied.append((host, socket, want))
            except Exception:
                pass
    return applied


def _loop():
    while not _stop.wait(_POLL_S):
        try:
            tick()
        except Exception:
            pass


def start() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="homepchub-sched", daemon=True)
    _thread.start()


def stop() -> None:
    _stop.set()


def demo():
    now = datetime(2026, 3, 15, 8, 30)
    daily = {"enabled": True, "kind": "daily", "time": "08:30", "action": "on"}
    assert evaluate_rule(daily, now) is True
    assert evaluate_rule(daily, now + timedelta(minutes=1)) is None

    weekly = {
        "enabled": True,
        "kind": "weekly",
        "time": "08:30",
        "weekdays": [6],  # Sunday - 2026-03-15 is Sunday
        "action": "off",
    }
    assert evaluate_rule(weekly, now) is False

    loop = {
        "enabled": True,
        "kind": "loop",
        "on_minutes": 10,
        "off_minutes": 10,
        "loop_start": now.isoformat(timespec="seconds"),
    }
    assert desired_loop_on(loop, now) is True
    assert desired_loop_on(loop, now + timedelta(minutes=10)) is False
    assert desired_loop_on(loop, now + timedelta(minutes=20)) is True

    once = {
        "enabled": True,
        "kind": "once",
        "date": "2026-03-15",
        "time": "08:30",
        "action": "on",
    }
    assert evaluate_rule(once, now) is True

    toggle = {
        "enabled": True,
        "kind": "daily",
        "time": "08:30",
        "action": "toggle",
    }
    assert evaluate_rule(toggle, now) == "toggle"
    print("ok")


if __name__ == "__main__":
    demo()
